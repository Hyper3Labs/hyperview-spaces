const sdk = globalThis.HyperViewPanelSDK;
if (!sdk) throw new Error("HyperViewPanelSDK is not available on window.");

const { React, components, hooks } = sdk;
const { Panel } = components;
const { usePanelCommands, usePanelProps, usePanelRuntimeState } = hooks;

const colors = {
  panelBg: "#10151f",
  cardBg: "#141b27",
  buttonBg: "#172132",
  border: "#334155",
  text: "#e5e7eb",
  strongText: "#f8fafc",
  mutedText: "#94a3b8",
  bodyText: "#cbd5e1",
  good: "#7dd3a7",
  goodBg: "#132018",
  accent: "#8fb8ff",
  error: "#fca5a5",
  warningBg: "#3b2f12",
  warningBorder: "#92400e",
  warningText: "#fde68a",
};

function pretty(value) {
  return String(value || "unlabeled").replaceAll("_", " ");
}

function title(value) {
  return pretty(value).replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeModels(value) {
  if (!Array.isArray(value)) return [];
  return value
    .map((model, index) => ({
      key: String(model.key || `model-${index}`),
      displayName: String(model.displayName || model.display_name || model.key || `Model ${index + 1}`),
      buttonLabel: String(model.buttonLabel || model.button_label || `${model.key || "Model"} query`),
      layoutKey: model.layoutKey || model.layout_key || null,
      spaceKey: model.spaceKey || model.space_key || null,
    }))
    .filter((model) => model.layoutKey);
}

function Badge({ children }) {
  return React.createElement(
    "span",
    {
      style: {
        alignSelf: "flex-start",
        border: `1px solid ${colors.border}`,
        borderRadius: 999,
        background: "transparent",
        color: colors.mutedText,
        padding: "2px 6px",
        fontSize: 9,
        fontWeight: 700,
        lineHeight: 1.2,
      },
    },
    children,
  );
}

function numberOrNull(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function signed(value, digits = 3) {
  if (!Number.isFinite(value)) return "n/a";
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function rankList(neighbors, predicate) {
  if (!Array.isArray(neighbors)) return [];
  return neighbors.filter(predicate).map((neighbor) => `#${neighbor.rank}`);
}

function PrimaryWin({ item }) {
  if (!item) return null;
  const hyper = item.summaries?.candidate || {};
  const clip = item.summaries?.clip || {};
  const hyperAp = numberOrNull(hyper.sameSkuNormalAp10);
  const clipAp = numberOrNull(clip.sameSkuNormalAp10);
  const hyperPipe = numberOrNull(hyper.pipeFryumConfusions);
  const clipPipe = numberOrNull(clip.pipeFryumConfusions);
  const apDelta = hyperAp !== null && clipAp !== null ? hyperAp - clipAp : null;
  const pipeDelta = hyperPipe !== null && clipPipe !== null ? clipPipe - hyperPipe : null;
  const clipPipeRanks = rankList(clip.neighbors, (neighbor) => neighbor.pipeFryumConfusion);
  const hyperNormalRanks = rankList(hyper.neighbors, (neighbor) => neighbor.sameSkuNormal);

  const metricBox = (label, value, tone = colors.good) =>
    React.createElement(
      "div",
      {
        style: {
          borderLeft: `2px solid ${tone}`,
          padding: "1px 0 1px 7px",
        },
      },
      React.createElement("div", { style: { color: colors.mutedText, fontSize: 9, textTransform: "uppercase", lineHeight: 1.1 } }, label),
      React.createElement("div", { style: { color: tone, fontSize: 18, fontWeight: 900, lineHeight: 1.05 } }, value),
    );

  return React.createElement(
    "div",
    {
      style: {
        borderTop: `1px solid ${colors.border}`,
        borderBottom: `1px solid ${colors.border}`,
        padding: "8px 0",
        display: "flex",
        flexDirection: "column",
        gap: 7,
      },
    },
    React.createElement("div", { style: { color: colors.strongText, fontSize: 12, fontWeight: 900 } }, "Step 3: The advantage"),
    React.createElement(
      "div",
      { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 6 } },
      metricBox("AP@10 lift", apDelta === null ? "n/a" : signed(apDelta), colors.good),
      metricBox("Fewer wrong-line refs", pipeDelta === null ? "n/a" : String(pipeDelta), colors.good),
    ),
    React.createElement(
      "div",
      { style: { color: colors.bodyText, fontSize: 10.5, lineHeight: 1.35 } },
      `Hyper3 puts same-SKU normal refs at ${hyperNormalRanks.slice(0, 3).join(", ") || "the top ranks"}. CLIP admits pipe_fryum at ${
        clipPipeRanks.join(", ") || "no displayed rank"
      }.`,
    ),
  );
}

function CompactEvidence({ item, models }) {
  if (!item) return null;
  const ordered = orderedWalkthroughModels(models);
  const cell = {
    padding: "5px 0",
    borderBottom: `1px solid ${colors.border}`,
    fontSize: 10.5,
    color: colors.bodyText,
  };
  const head = { ...cell, color: colors.mutedText, fontSize: 9, textTransform: "uppercase" };
  return React.createElement(
    "table",
    { style: { width: "100%", borderCollapse: "collapse" } },
    React.createElement(
      "thead",
      null,
      React.createElement(
        "tr",
        null,
        React.createElement("th", { style: head, align: "left" }, "Model"),
        React.createElement("th", { style: head, align: "right" }, "AP@10"),
        React.createElement("th", { style: head, align: "right" }, "Wrong-line"),
      ),
    ),
    React.createElement(
      "tbody",
      null,
      ordered.map((model) => {
        const summary = item?.summaries?.[model.key] || {};
        const isHyper3 = model.key === "candidate";
        const badCount = summary.pipeFryumConfusions ?? "n/a";
        const ap = summary.sameSkuNormalAp10 ?? "n/a";
        return React.createElement(
          "tr",
          { key: `${item.id}-${model.key}-compact` },
          React.createElement("td", { style: { ...cell, color: colors.strongText, fontWeight: 800 } }, model.displayName),
          React.createElement("td", { style: { ...cell, color: isHyper3 ? colors.good : colors.accent, fontWeight: 900 }, align: "right" }, ap),
          React.createElement("td", { style: { ...cell, color: badCount === 0 ? colors.good : colors.error, fontWeight: 900 }, align: "right" }, badCount),
        );
      }),
    ),
  );
}

function StepBlock({ number, title, children }) {
  return React.createElement(
    "div",
    {
      style: {
        display: "grid",
        gridTemplateColumns: "22px minmax(0, 1fr)",
        gap: 8,
        alignItems: "start",
      },
    },
    React.createElement(
      "div",
      {
        style: {
          width: 18,
          height: 18,
          borderRadius: 999,
          border: `1px solid ${colors.border}`,
          color: colors.mutedText,
          display: "grid",
          placeItems: "center",
          fontSize: 10,
          fontWeight: 900,
          marginTop: 1,
        },
      },
      number,
    ),
    React.createElement(
      "div",
      { style: { minWidth: 0 } },
      React.createElement("div", { style: { color: colors.strongText, fontSize: 11.5, fontWeight: 900, marginBottom: 2 } }, title),
      React.createElement("div", { style: { color: colors.bodyText, fontSize: 10.5, lineHeight: 1.3 } }, children),
    ),
  );
}

function StrengthTable({ rows }) {
  if (!Array.isArray(rows) || rows.length === 0) return null;
  const cell = {
    padding: "4px 4px",
    borderBottom: `1px solid ${colors.border}`,
    fontSize: 10,
    color: colors.bodyText,
  };
  const head = { ...cell, color: colors.mutedText, fontSize: 9, textTransform: "uppercase", letterSpacing: 0.4 };
  return React.createElement(
    "div",
    {
      style: {
        borderTop: `1px solid ${colors.border}`,
        paddingTop: 8,
      },
    },
    React.createElement(
      "div",
      { style: { color: colors.strongText, fontSize: 12, fontWeight: 800, marginBottom: 5 } },
      "Where Hyper3 Wins On VisA",
    ),
    React.createElement(
      "div",
      { style: { color: colors.mutedText, fontSize: 10, lineHeight: 1.3, marginBottom: 6 } },
      "Top current-run gains for same-SKU normal reference AP. This is reference lookup, not defect segmentation.",
    ),
    React.createElement(
      "table",
      { style: { width: "100%", borderCollapse: "collapse" } },
      React.createElement(
        "thead",
        null,
        React.createElement(
          "tr",
          null,
          React.createElement("th", { style: head, align: "left" }, "SKU"),
          React.createElement("th", { style: head, align: "right" }, "H3"),
          React.createElement("th", { style: head, align: "right" }, "CLIP"),
          React.createElement("th", { style: head, align: "right" }, "Delta"),
        ),
      ),
      React.createElement(
        "tbody",
        null,
        rows.map((row) =>
          React.createElement(
            "tr",
            { key: row.category },
            React.createElement("td", { style: cell }, row.category),
            React.createElement("td", { style: { ...cell, color: colors.good }, align: "right" }, row.hyper3),
            React.createElement("td", { style: cell, align: "right" }, row.clip),
            React.createElement("td", { style: { ...cell, color: colors.good }, align: "right" }, row.delta),
          ),
        ),
      ),
    ),
  );
}

function advantageMetric(modelKey, itemId) {
  if (itemId === "fryum" && modelKey === "candidate") {
    return {
      line: "Visible walkthrough: same-SKU normal ref at rank #1",
      text: "Hyper3 starts with Fryum normal references and keeps pipe_fryum wrong-line variants out of the early neighborhood.",
    };
  }
  if (itemId === "fryum" && modelKey === "clip") {
    return {
      line: "Visible walkthrough: pipe_fryum enters the top neighborhood",
      text: "CLIP starts with another Fryum test image, then admits pipe_fryum wrong-line variants in the top-10 neighborhood.",
    };
  }
  if (modelKey === "candidate") {
    return {
      line: "Macaroni2 same-SKU mAP: 1.0000",
      text: "Hyper3 keeps same-SKU Macaroni2 references ranked ahead more consistently across the Macaroni2 query set.",
    };
  }
  if (modelKey === "clip") {
    return {
      line: "Macaroni2 same-SKU mAP: 0.9377",
      text: "CLIP is the baseline; visually similar wrong-line items move up more often across the Macaroni2 query set.",
    };
  }
  return null;
}

function orderedWalkthroughModels(models) {
  return [...models].sort((left, right) => {
    const order = { candidate: 0, clip: 1 };
    return (order[left.key] ?? 10) - (order[right.key] ?? 10);
  });
}

function choiceFromSimilarity(similarity, examples, models) {
  if (!similarity) return null;
  const sampleId = similarity.anchor_sample_id || similarity.sample_id;
  const item = examples.find((example) => example.queryId === sampleId);
  if (!item) return null;
  const source = String(similarity.source || "");
  const sourceKey = source.includes(":") ? source.split(":").pop() : null;
  const model =
    models.find((candidate) => candidate.key === sourceKey) ||
    models.find((candidate) => candidate.layoutKey === similarity.layout_key) ||
    models.find((candidate) => candidate.spaceKey === similarity.space_key);
  if (!model) return null;
  const metric = advantageMetric(model.key, item.id);
  return {
    modelKey: model.key,
    modelName: model.displayName,
    queryLabel: title(item.queryLabel || item.id),
    metricLine: metric?.line || null,
  };
}

async function sendJson(path, payload, method = "POST") {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function buttonText(model) {
  if (model.key === "candidate") return "Hyper3";
  if (model.key === "clip") return "CLIP";
  return model.displayName.replace("-CLIP", "");
}

function WalkthroughCard({ item, models, onSelectQuery, loadingKey, activeModelKey }) {
  if (!item) return null;
  return React.createElement(
    "div",
    {
      style: {
        display: "flex",
        flexDirection: "column",
        gap: 9,
      },
    },
    React.createElement(
      "div",
      { style: { display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" } },
      React.createElement(
        "div",
        { style: { color: colors.strongText, fontSize: 14, fontWeight: 900 } },
        "Fryum Reference Lookup",
      ),
      React.createElement(Badge, null, "VisA"),
    ),
    React.createElement(StepBlock, { number: "1", title: "Inspection Query" }, "Fryum part from VisA. The QA task is to find normal Fryum references, not visually similar wrong-line parts."),
    React.createElement(
      StepBlock,
      { number: "2", title: "Run Both Embeddings" },
      "Click Hyper3 first, then CLIP. The Samples panel should switch to the top neighbors for the same query.",
    ),
    React.createElement(
      "div",
      { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 6 } },
      orderedWalkthroughModels(models).map((model) => {
        const choiceKey = `${item.queryId}:${model.key}`;
        const isHyper3 = model.key === "candidate";
        const isActive = activeModelKey === model.key;
        return React.createElement(
          "button",
          {
            key: choiceKey,
            type: "button",
            onClick: () => onSelectQuery(item.queryId, model),
            disabled: loadingKey === choiceKey,
            title: `Show ${model.displayName} nearest references for Fryum`,
            style: {
              border: `1px solid ${isActive ? (isHyper3 ? colors.good : colors.accent) : colors.border}`,
              background: isActive ? (isHyper3 ? colors.goodBg : colors.buttonBg) : "transparent",
              color: isActive ? colors.strongText : colors.bodyText,
              borderRadius: 5,
              padding: "7px 8px",
              fontSize: 11,
              lineHeight: 1.25,
              cursor: loadingKey === choiceKey ? "default" : "pointer",
              textAlign: "center",
              fontWeight: 800,
              opacity: loadingKey === choiceKey ? 0.65 : 1,
            },
          },
          loadingKey === choiceKey ? "Loading..." : buttonText(model),
        );
      }),
    ),
    React.createElement(PrimaryWin, { item }),
    React.createElement(
      "div",
      { style: { color: colors.mutedText, fontSize: 10, lineHeight: 1.3 } },
      "Wrong-line references send operators to the wrong golden sample.",
    ),
    React.createElement(CompactEvidence, { item, models }),
  );
}

export default function ManufacturingPanel() {
  const props = usePanelProps() || {};
  const commands = usePanelCommands();
  const runtimeState = usePanelRuntimeState ? usePanelRuntimeState() : {};
  const workspaceId = String(props.workspaceId || props.workspace_id || "manufacturing-visa-reference-clip-hyper3clip");
  const models = normalizeModels(props.models);
  const examples = Array.isArray(props.examples) ? props.examples : [];
  const primaryExample = examples.find((item) => item.id === "fryum") || examples[0] || null;
  const warnings = Array.isArray(props.warnings) ? props.warnings : [];
  const [loadingKey, setLoadingKey] = React.useState(null);
  const [panelError, setPanelError] = React.useState(null);
  const [activeChoice, setActiveChoice] = React.useState(null);
  const [activeModelKey, setActiveModelKey] = React.useState(null);
  const statusChoice = choiceFromSimilarity(runtimeState.activeSimilarityQuery, examples, models) || activeChoice;

  const onSelectQuery = React.useCallback(
    async (sampleId, model) => {
      if (!sampleId || !model.layoutKey) {
        setPanelError("Could not show neighbors: this example is missing a query or layout key.");
        return;
      }
      if (!commands) {
        setPanelError("Could not show neighbors: HyperView panel commands are unavailable in this panel host.");
        return;
      }
      const choiceKey = `${sampleId}:${model.key}`;
      const item = examples.find((example) => example.queryId === sampleId);
      const metric = advantageMetric(model.key, item?.id);
      const nextChoice = {
        modelName: model.displayName,
        queryLabel: title(item?.queryLabel || "fryum"),
        metricLine: metric?.line || null,
      };
      setPanelError(null);
      setActiveModelKey(model.key);
      setActiveChoice(nextChoice);
      setLoadingKey(choiceKey);
      try {
        if (commands.setActiveLayout) {
          await commands.setActiveLayout(model.layoutKey, { persist: "none" });
        }
        if (commands.showSimilar) {
          await commands.showSimilar({
            sampleId,
            layoutKey: model.layoutKey,
            spaceKey: model.spaceKey,
            k: 10,
            source: `manufacturing-demo:${model.key}`,
            focus: "samples",
            persist: "none",
          });
        }
        await sendJson("/api/control/ui/state", {
          workspace_id: workspaceId,
          set_active_layout: true,
          active_layout_key: model.layoutKey,
          set_selection: true,
          selected_ids: [sampleId],
          set_similarity_query: true,
          similarity_query: {
            sample_id: sampleId,
            layout_key: model.layoutKey,
            space_key: model.spaceKey,
            k: 10,
            source: `manufacturing-demo:${model.key}`,
          },
        }, "PATCH");
        setActiveChoice(nextChoice);
        setActiveModelKey(model.key);
      } catch (error) {
        try {
          await sendJson("/api/control/ui/layout", {
            workspace_id: workspaceId,
            layout_key: model.layoutKey,
          });
          await sendJson("/api/control/ui/similarity", {
            workspace_id: workspaceId,
            sample_id: sampleId,
            layout_key: model.layoutKey,
            space_key: model.spaceKey,
            k: 10,
            source: `manufacturing-demo:${model.key}`,
          });
          setActiveChoice(nextChoice);
          setActiveModelKey(model.key);
          return;
        } catch (fallbackError) {
          const message = fallbackError instanceof Error ? fallbackError.message : String(fallbackError);
          setPanelError(`Could not show neighbors: ${message}`);
        }
      } finally {
        setLoadingKey(null);
      }
    },
    [commands, examples, workspaceId],
  );

  return React.createElement(
    Panel,
    {
      style: {
        background: colors.panelBg,
        color: colors.text,
        height: "100%",
        minHeight: 0,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      },
    },
    React.createElement(
      "div",
      {
        style: {
          display: "flex",
          flexDirection: "column",
          gap: 9,
          padding: 10,
          minHeight: 0,
          overflowY: "auto",
          scrollbarGutter: "stable",
        },
      },
      React.createElement(
        "div",
        { style: { color: colors.strongText, fontSize: 14, fontWeight: 900 } },
        "VisA QA Reference Lookup",
      ),
      React.createElement(
        "div",
        { style: { color: colors.mutedText, fontSize: 10.5, lineHeight: 1.3 } },
        "Goal: retrieve the right normal reference before similar wrong-line parts.",
      ),
      React.createElement(WalkthroughCard, {
        item: primaryExample,
        models,
        loadingKey,
        activeModelKey: activeModelKey || statusChoice?.modelKey,
        onSelectQuery,
      }),
      statusChoice
        ? React.createElement(
            "div",
            {
              style: {
                borderLeft: `2px solid ${colors.good}`,
                color: colors.good,
                padding: "2px 0 2px 7px",
                fontSize: 10.5,
                lineHeight: 1.3,
              },
            },
            `Current view: ${statusChoice.modelName} neighbors for ${statusChoice.queryLabel}. ${
              statusChoice.metricLine || "The selected query and top references should now be visible in the Samples view."
            }`,
          )
        : null,
      panelError
        ? React.createElement(
            "div",
            { style: { color: colors.error, fontSize: 11, lineHeight: 1.35 } },
            panelError,
          )
        : null,
      warnings.map((warning, index) =>
        React.createElement(
          "div",
          {
            key: index,
            style: {
              border: `1px solid ${colors.warningBorder}`,
              background: colors.warningBg,
              color: colors.warningText,
              borderRadius: 5,
              padding: 8,
              fontSize: 11,
              lineHeight: 1.35,
            },
          },
          warning,
        ),
      ),
      React.createElement(StrengthTable, { rows: Array.isArray(props.strengthRows) ? props.strengthRows : [] }),
    ),
  );
}
