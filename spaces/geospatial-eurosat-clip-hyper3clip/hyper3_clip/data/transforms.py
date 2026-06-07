from __future__ import annotations

from torchvision import transforms


IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
CLIP_MEAN = (0.48145466, 0.4578275, 0.40821073)
CLIP_STD = (0.26862954, 0.26130258, 0.27577711)
SIGLIP_MEAN = (0.5, 0.5, 0.5)
SIGLIP_STD = (0.5, 0.5, 0.5)


def normalization_stats(normalization: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if normalization == "imagenet":
        return IMAGENET_MEAN, IMAGENET_STD
    if normalization == "clip":
        return CLIP_MEAN, CLIP_STD
    if normalization == "siglip":
        return SIGLIP_MEAN, SIGLIP_STD
    raise ValueError("normalization must be one of 'imagenet', 'clip', or 'siglip'")


def build_train_transform(
    image_size: int,
    preset: str = "wide_random_crop",
    normalization: str = "imagenet",
) -> transforms.Compose:
    if preset == "wide_random_crop":
        steps = [
            transforms.RandomResizedCrop(
                size=image_size,
                scale=(0.5, 1.0),
                interpolation=transforms.InterpolationMode.BICUBIC,
            ),
            transforms.ToTensor(),
        ]
    elif preset == "wide_random_crop_light_color":
        steps = [
            transforms.RandomResizedCrop(
                size=image_size,
                scale=(0.5, 1.0),
                interpolation=transforms.InterpolationMode.BICUBIC,
            ),
            transforms.RandomApply(
                [
                    transforms.ColorJitter(
                        brightness=0.2,
                        contrast=0.2,
                        saturation=0.2,
                        hue=0.05,
                    )
                ],
                p=0.4,
            ),
            transforms.ToTensor(),
        ]
    elif preset == "medium_random_crop":
        steps = [
            transforms.RandomResizedCrop(
                size=image_size,
                scale=(0.6, 1.0),
                interpolation=transforms.InterpolationMode.BICUBIC,
            ),
            transforms.ToTensor(),
        ]
    elif preset == "center_crop":
        steps = [
            transforms.Resize(image_size, interpolation=transforms.InterpolationMode.BICUBIC),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
        ]
    elif preset == "tight_crop_color_jitter_gray":
        steps = [
            transforms.RandomResizedCrop(
                size=image_size,
                scale=(0.8, 1.0),
                interpolation=transforms.InterpolationMode.BICUBIC,
            ),
            transforms.RandomApply(
                [
                    transforms.ColorJitter(
                        brightness=0.4,
                        contrast=0.4,
                        saturation=0.4,
                        hue=0.1,
                    )
                ],
                p=0.8,
            ),
            transforms.RandomGrayscale(p=0.2),
            transforms.ToTensor(),
        ]
    else:
        raise ValueError(
            f"Unsupported train transform preset {preset!r}; "
            "expected 'wide_random_crop', 'wide_random_crop_light_color', "
            "'medium_random_crop', 'tight_crop_color_jitter_gray', or 'center_crop'"
        )

    mean, std = normalization_stats(normalization)
    return transforms.Compose([*steps, transforms.Normalize(mean=mean, std=std)])


def build_eval_transform(image_size: int, normalization: str = "imagenet") -> transforms.Compose:
    mean, std = normalization_stats(normalization)
    return transforms.Compose(
        [
            transforms.Resize(image_size, interpolation=transforms.InterpolationMode.BICUBIC),
            transforms.CenterCrop(image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ]
    )


def build_retrieval_transform(image_size: int, normalization: str = "imagenet") -> transforms.Compose:
    mean, std = normalization_stats(normalization)
    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size), interpolation=transforms.InterpolationMode.BICUBIC),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ]
    )
