from __future__ import annotations

import csv
import pickle
from pathlib import Path

import networkx as nx
import torch
from torch.utils.data import DataLoader, Subset
from torchvision import datasets

from hyper3_clip.data.transforms import build_eval_transform
from hyper3_clip.evaluation.classification import IMAGENET_PROMPTS, _build_text_classifier, _imagenet_prompt_names, _looks_like_wnid
from hyper3_clip.models.hyper3_clip import Hyper3CLIP


@torch.inference_mode()
def evaluate_imagenet_hierarchical(
    model: Hyper3CLIP,
    imagenet_val_root: str | Path,
    assets_root: str | Path,
    device: torch.device,
    batch_size: int = 128,
    image_size: int = 224,
    max_text_length: int = 77,
    max_items: int | None = None,
    prompts: tuple[str, ...] = IMAGENET_PROMPTS,
) -> dict[str, float]:
    model.eval()
    imagenet_root = Path(imagenet_val_root)
    dataset = datasets.ImageFolder(str(imagenet_root), transform=build_eval_transform(image_size))
    class_names = _imagenet_prompt_names(dataset.classes, imagenet_root)
    classifier = _build_text_classifier(model, class_names, prompts, device, max_text_length)
    eval_dataset = Subset(dataset, range(min(max_items, len(dataset)))) if max_items is not None else dataset
    loader = DataLoader(eval_dataset, batch_size=batch_size, num_workers=4, pin_memory=device.type == "cuda")

    assets_path = Path(assets_root)
    synsets_ordering = pickle.load((assets_path / "all_synsets.pkl").open("rb"))
    ancestor_indices = pickle.load((assets_path / "all_ancestors_indices.pkl").open("rb"))
    graph = _create_graph_from_edges(assets_path / "imagenet_isa.txt")
    dataset_to_official = _dataset_to_official_indices(dataset.classes, imagenet_root, synsets_ordering).to(device)

    totals = torch.zeros(5, dtype=torch.float64)
    total_count = 0
    for images, targets in loader:
        images = images.to(device, non_blocking=True)
        official_targets = dataset_to_official[targets.to(device, non_blocking=True)]
        dataset_predictions = model.similarity_scores(model.encode_image(images), classifier).argmax(dim=1)
        official_predictions = dataset_to_official[dataset_predictions]
        batch_totals = _hierarchical_totals(
            official_predictions.cpu().tolist(),
            official_targets.cpu().tolist(),
            ancestor_indices,
            graph,
            synsets_ordering,
        )
        totals += torch.tensor(batch_totals, dtype=torch.float64)
        total_count += int(official_targets.numel())

    averages = totals / max(total_count, 1)
    return {
        "tie": float(averages[0].item()),
        "lca": float(averages[1].item()),
        "jaccard": float(averages[2].item()),
        "hierarchical_precision": float(averages[3].item()),
        "hierarchical_recall": float(averages[4].item()),
    }


def _create_graph_from_edges(edge_file: Path) -> nx.DiGraph:
    graph = nx.DiGraph()
    with edge_file.open("r", encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter=" ")
        for parent, child in reader:
            graph.add_edge(parent, child)
    return graph


def _dataset_to_official_indices(class_names: list[str], imagenet_val_root: Path, synsets_ordering: list[str]) -> torch.Tensor:
    label_index = imagenet_val_root / "imagenet_label_to_wnid.tsv"
    if label_index.exists():
        wnid_to_label = {}
        for line in label_index.read_text(encoding="utf-8").splitlines():
            label, wnid = line.split("\t", maxsplit=1)
            wnid_to_label[wnid] = int(label)
        return torch.tensor([wnid_to_label[class_name] for class_name in class_names], dtype=torch.long)
    if all(_looks_like_wnid(class_name) for class_name in class_names):
        synset_to_label = {synset: label for label, synset in enumerate(synsets_ordering)}
        return torch.tensor([synset_to_label[class_name] for class_name in class_names], dtype=torch.long)
    return torch.arange(len(class_names), dtype=torch.long)


def _hierarchical_totals(
    predicted_labels: list[int],
    true_labels: list[int],
    ancestor_indices: list[list[int]],
    graph: nx.DiGraph,
    synsets_ordering: list[str],
) -> tuple[float, float, float, float, float]:
    undirected_graph = graph.to_undirected()
    tree_induced_error = 0.0
    least_common_ancestor = 0.0
    jaccard = 0.0
    hierarchical_precision = 0.0
    hierarchical_recall = 0.0
    for pred_label, true_label in zip(predicted_labels, true_labels):
        pred_synset = synsets_ordering[pred_label]
        true_synset = synsets_ordering[true_label]
        pred_ancestors = set(ancestor_indices[pred_label])
        true_ancestors = set(ancestor_indices[true_label])
        intersection = pred_ancestors.intersection(true_ancestors)
        union = pred_ancestors.union(true_ancestors)
        tree_induced_error += nx.shortest_path_length(undirected_graph, source=pred_synset, target=true_synset)
        least_common_ancestor += len(pred_ancestors) - len(intersection) + 1
        jaccard += len(intersection) / len(union)
        hierarchical_precision += len(intersection) / len(pred_ancestors)
        hierarchical_recall += len(intersection) / len(true_ancestors)
    return tree_induced_error, least_common_ancestor, jaccard, hierarchical_precision, hierarchical_recall
