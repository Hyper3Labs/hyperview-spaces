import { rankedResults } from "./ranked_results.js";

const sdk = globalThis.HyperViewPanelSDK;
if (!sdk) throw new Error("HyperViewPanelSDK is not available on window.");

const { React, components, hooks } = sdk;
const { Panel, PanelToolbar, PanelToolbarButton } = components;
const {
  usePanelSelection,
  usePanelSamples,
  usePanelCommands,
  usePanelProps,
} = hooks;

const colors = {
  panelBg: "#111827",
  cardBg: "#161f2d",
  buttonBg: "#1f2937",
  border: "#334155",
  text: "#e5e7eb",
  strongText: "#f8fafc",
  mutedText: "#9ca3af",
  bodyText: "#cbd5e1",
  accent: "#93c5fd",
  success: "#86efac",
  error: "#fca5a5",
};

function Section({ title, children }) {
  return React.createElement(
    "section",
    { style: { display: "flex", flexDirection: "column", gap: 8 } },
    React.createElement(
      "h3",
      {
        style: {
          margin: 0,
          color: colors.strongText,
          fontSize: 13,
          fontWeight: 700,
        },
      },
      title,
    ),
    children,
  );
}

function TextBlock({ children }) {
  return React.createElement(
    "div",
    { style: { color: colors.bodyText, fontSize: 12, lineHeight: 1.45 } },
    children,
  );
}

function normalizeModels(value) {
  if (!Array.isArray(value)) return [];
  return value.map((model, index) => ({
    key: String(model.key || `model-${index}`),
    displayName: String(model.displayName || model.display_name || model.key || `Model ${index + 1}`),
    buttonLabel: String(
      model.buttonLabel || model.button_label || `${model.displayName || model.key || "Model"} query`,
    ),
    layoutKey: model.layoutKey || model.layout_key || null,
    spaceKey: model.spaceKey || model.space_key || null,
  }));
}

function getSummary(item, modelKey) {
  return item.summaries?.[modelKey] || item.modelSummaries?.[modelKey] || {};
}

function rankLabel(rank) {
  return rank === 0 || rank ? `#${rank}` : "-";
}

function pct(value) {
  if (typeof value !== "number") return "-";
  return `${(value * 100).toFixed(1)}%`;
}

function metricValue(value, kind = "pct") {
  if (typeof value !== "number") return "-";
  if (kind === "decimal") return value.toFixed(3);
  return pct(value);
}

function modelAccent(model) {
  return model.key === "candidate" ? colors.success : colors.bodyText;
}

function modelBorder(model) {
  return model.key === "candidate" ? "#3f6f5b" : colors.border;
}

function MetricGrid({ rows }) {
  return React.createElement(
    "div",
    {
      style: {
        display: "grid",
        gridTemplateColumns: "1.5fr 1fr 1fr",
        border: `1px solid ${colors.border}`,
        borderRadius: 6,
        overflow: "hidden",
        fontSize: 11,
      },
    },
    React.createElement("div", { style: headerCellStyle() }, "Metric"),
    React.createElement("div", { style: headerCellStyle() }, "Hyper3"),
    React.createElement("div", { style: headerCellStyle() }, "CLIP"),
    rows.flatMap((row) => [
      React.createElement("div", { key: `${row.label}-label`, style: bodyCellStyle() }, row.label),
      React.createElement(
        "div",
        { key: `${row.label}-h`, style: bodyCellStyle(colors.success) },
        metricValue(row.hyper3, row.kind),
      ),
      React.createElement(
        "div",
        { key: `${row.label}-c`, style: bodyCellStyle() },
        metricValue(row.clip, row.kind),
      ),
    ]),
  );
}

function headerCellStyle() {
  return {
    background: "#0f172a",
    borderBottom: `1px solid ${colors.border}`,
    color: colors.strongText,
    fontWeight: 700,
    padding: 7,
  };
}

function bodyCellStyle(color = colors.bodyText) {
  return {
    borderTop: `1px solid ${colors.border}`,
    color,
    padding: 7,
  };
}

function ExampleChooser({ examples, selectedId, onSelect, compact = false }) {
  return React.createElement(
    "div",
    { style: { display: "grid", gridTemplateColumns: "1fr", gap: compact ? 5 : 6 } },
    examples.map((item) => {
      const active = item.id === selectedId;
      return React.createElement(
        "button",
        {
          key: item.id,
          type: "button",
          onClick: () => onSelect(item.id),
          style: {
            border: `1px solid ${active ? colors.accent : colors.border}`,
            background: active ? "rgba(147, 197, 253, 0.08)" : colors.cardBg,
            color: colors.text,
            borderRadius: 5,
            padding: compact ? "6px 7px" : "7px 8px",
            textAlign: "left",
            cursor: "pointer",
          },
        },
        React.createElement(
          "div",
          { style: { color: colors.strongText, fontSize: 12, fontWeight: 700, marginBottom: 2 } },
          item.title,
        ),
        React.createElement(
          "div",
          {
            style: {
              color: colors.bodyText,
              fontSize: 10,
              lineHeight: 1.3,
              overflow: "hidden",
              display: "-webkit-box",
              WebkitLineClamp: compact ? 2 : 1,
              WebkitBoxOrient: "vertical",
            },
          },
          item.query,
        ),
      );
    }),
  );
}

function ResultCard({ result, model, loadingKey, onSelectResult, compact = false, spacious = false }) {
  const choiceKey = `${result.sampleId}:${model.key}:ranked-result`;
  const cardBasis = compact ? 72 : spacious ? 102 : 84;
  const imageHeight = compact ? 78 : spacious ? 108 : 90;
  return React.createElement(
    "button",
    {
      type: "button",
      onClick: () => onSelectResult(result, model),
      disabled: loadingKey === choiceKey,
      title: `Select rank ${result.rank} in ${model.displayName}`,
      style: {
        width: cardBasis,
        minWidth: compact ? 66 : 78,
        maxWidth: spacious ? 122 : 104,
        flex: `1 1 ${cardBasis}px`,
        border: `1px solid ${result.isTarget ? colors.success : colors.border}`,
        background: result.isTarget ? "rgba(134, 239, 172, 0.06)" : "#0f172a",
        color: colors.text,
        borderRadius: 5,
        padding: 4,
        textAlign: "left",
        cursor: loadingKey === choiceKey ? "default" : "pointer",
        opacity: loadingKey === choiceKey ? 0.65 : 1,
      },
    },
    React.createElement(
      "div",
      {
        style: {
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 4,
          marginBottom: 4,
        },
      },
      React.createElement(
        "span",
        { style: { color: colors.strongText, fontSize: 10, fontWeight: 700 } },
        `#${result.rank}`,
      ),
      result.isTarget
        ? React.createElement(
            "span",
            { style: { color: colors.success, fontSize: 8, fontWeight: 700 } },
            "target",
          )
        : null,
    ),
    React.createElement("img", {
      src: result.image,
      alt: `${model.displayName} rank ${result.rank}`,
      style: {
        width: "100%",
        height: imageHeight,
        objectFit: "cover",
        borderRadius: 3,
        background: "#ffffff",
        display: "block",
        marginBottom: 4,
      },
    }),
    React.createElement(
      "div",
      {
        style: {
          color: colors.mutedText,
          fontSize: 8,
          lineHeight: 1.2,
          overflow: "hidden",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
        },
      },
      `${result.color || "unknown"} ${result.category || ""}`.trim(),
    ),
  );
}

function RankedResultStrip({ item, model, rows, targetRank, loadingKey, onSelectResult, compact = false, spacious = false }) {
  return React.createElement(
    "div",
    {
      style: {
        border: `1px solid ${modelBorder(model)}`,
        borderRadius: 6,
        background: colors.cardBg,
        padding: compact ? 6 : 7,
        display: "flex",
        flexDirection: "column",
        gap: 6,
      },
    },
    React.createElement(
      "div",
      { style: { display: "flex", justifyContent: "space-between", gap: 8, alignItems: "baseline" } },
      React.createElement(
        "div",
        { style: { color: colors.strongText, fontSize: 12, fontWeight: 700 } },
        model.displayName,
      ),
      React.createElement(
        "div",
        { style: { color: modelAccent(model), fontSize: 11, fontWeight: 700 } },
        `exact target ${rankLabel(targetRank)}`,
      ),
    ),
    React.createElement(
      "div",
      { style: { display: "flex", gap: compact ? 5 : 7, overflowX: "auto", paddingBottom: 2 } },
      rows.map((result) =>
        React.createElement(ResultCard, {
          key: `${item.id}-${model.key}-${result.rank}-${result.itemId}`,
          result,
          model,
          loadingKey,
          onSelectResult,
          compact,
          spacious,
        }),
      ),
    ),
  );
}

function SearchResultComparison({ item, models, loadingKey, onSelectResult, compact = false, spacious = false }) {
  const proof = rankedResults[item.id];
  const hasInspectableLayouts = models.some((model) => model.layoutKey);
  if (!proof) {
    return React.createElement(
      "div",
      { style: { color: colors.bodyText, fontSize: 12, lineHeight: 1.45 } },
      "Ranked results are not configured for this query.",
    );
  }

  return React.createElement(
    "div",
    { style: { display: "flex", flexDirection: "column", gap: compact ? 6 : 7 } },
    React.createElement(
      "div",
      {
        style: {
        border: `1px solid ${colors.border}`,
        borderRadius: 5,
        background: "#0f172a",
          padding: compact ? 6 : 7,
          color: colors.bodyText,
          fontSize: 11,
          lineHeight: 1.35,
        },
      },
      React.createElement("strong", { style: { color: colors.strongText } }, "Selected query: "),
      item.query,
      React.createElement(
        "div",
        { style: { color: colors.mutedText, fontSize: 10, marginTop: 3 } },
        hasInspectableLayouts
          ? "Green card = exact product. Click a card to inspect it in Samples and the model neighborhood."
          : "Green card = exact product. Click a card to select it in Samples.",
      ),
    ),
    models.map((model) =>
      React.createElement(RankedResultStrip, {
        key: `${item.id}-${model.key}-ranked-results`,
        item,
        model,
        rows: proof.results?.[model.key] || [],
        targetRank: proof.targetRanks?.[model.key],
        loadingKey,
        onSelectResult,
        compact,
        spacious,
      }),
    ),
  );
}

function ExactTargetActions({ item, models, loadingKey, onSelectQuery, compact = false }) {
  const gridColumns = compact ? "1fr" : "repeat(auto-fit, minmax(220px, 1fr))";

  return React.createElement(
    "div",
    { style: { display: "grid", gridTemplateColumns: gridColumns, gap: 7 } },
      models.map((model) => {
        const summary = getSummary(item, model.key);
        const isCandidate = model.key === "candidate";
        const targetRank = rankLabel(summary.rank);
        const neighborLine =
          typeof summary.categoryHits === "number"
            ? `${summary.categoryHits}/${summary.total || 10} same-category image neighbors`
            : "Neighbor context available in HyperView";
        const choiceKey = `${item.queryId}:${model.key}`;
        return React.createElement(
          "button",
          {
            key: model.key,
            type: "button",
            onClick: () => onSelectQuery(item, model),
            disabled: loadingKey === choiceKey,
            title: `Select target item for ${model.displayName}`,
            style: {
              border: `1px solid ${modelBorder(model)}`,
              borderRadius: 5,
              padding: compact ? 7 : 8,
              background: isCandidate ? "rgba(134, 239, 172, 0.06)" : "transparent",
              color: colors.text,
              textAlign: "left",
              cursor: loadingKey === choiceKey ? "default" : "pointer",
              opacity: loadingKey === choiceKey ? 0.65 : 1,
            },
          },
          React.createElement(
            "div",
            { style: { display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 4 } },
            React.createElement(
              "span",
              { style: { color: colors.strongText, fontSize: 12, fontWeight: 700 } },
              model.displayName,
            ),
            React.createElement(
              "span",
              { style: { color: modelAccent(model), fontSize: 11, fontWeight: 700 } },
              `target ${targetRank}`,
            ),
          ),
          React.createElement(
            "div",
            { style: { color: isCandidate ? colors.success : colors.bodyText, fontSize: 11, lineHeight: 1.35 } },
            summary.text || "",
          ),
          React.createElement(
            "div",
            { style: { color: colors.mutedText, fontSize: 10, lineHeight: 1.35, marginTop: 5 } },
            loadingKey === choiceKey ? "Loading map selection..." : neighborLine,
          ),
        );
      }),
  );
}

function RailBlock({ title, children }) {
  return React.createElement(
    "div",
    {
      style: {
        border: `1px solid ${colors.border}`,
        borderRadius: 6,
        background: colors.cardBg,
        padding: 10,
        display: "flex",
        flexDirection: "column",
        gap: 7,
      },
    },
    React.createElement(
      "div",
      { style: { color: colors.strongText, fontSize: 11, fontWeight: 700 } },
      title,
    ),
    children,
  );
}

function MiniStat({ label, value, accent = false }) {
  return React.createElement(
    "div",
    {
      style: {
        border: `1px solid ${accent ? "#3f6f5b" : colors.border}`,
        borderRadius: 5,
        background: accent ? "rgba(134, 239, 172, 0.05)" : "#0f172a",
        padding: 8,
      },
    },
    React.createElement(
      "div",
      { style: { color: colors.mutedText, fontSize: 9, fontWeight: 700, textTransform: "uppercase" } },
      label,
    ),
    React.createElement(
      "div",
      { style: { color: accent ? colors.success : colors.strongText, fontSize: 17, fontWeight: 800, marginTop: 3 } },
      value,
    ),
  );
}

function BusinessRail({ item, metrics, fill = false }) {
  if (!item) return null;
  const clipSummary = getSummary(item, "clip");
  const candidateSummary = getSummary(item, "candidate");

  return React.createElement(
    "aside",
    {
      style: {
        flex: fill ? "none" : "0 1 280px",
        width: fill ? "100%" : undefined,
        minWidth: fill ? 0 : 240,
        maxWidth: fill ? "none" : 300,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      },
    },
    React.createElement(
      RailBlock,
      { title: "Buyer Readout" },
      React.createElement(
        "div",
        { style: { color: colors.bodyText, fontSize: 11, lineHeight: 1.4 } },
        item.targetTitle,
      ),
      React.createElement(
        "div",
        { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 7 } },
        React.createElement(MiniStat, {
          label: "Hyper3 Target",
          value: rankLabel(candidateSummary.rank),
          accent: true,
        }),
        React.createElement(MiniStat, {
          label: "CLIP Target",
          value: rankLabel(clipSummary.rank),
        }),
      ),
      React.createElement(
        "div",
        { style: { color: colors.mutedText, fontSize: 10, lineHeight: 1.4 } },
        candidateSummary.text || "Exact target appears earlier in the ranked product results.",
      ),
    ),
    React.createElement(
      RailBlock,
      { title: "Why This Query Matters" },
      React.createElement(
        "div",
        { style: { color: colors.bodyText, fontSize: 11, lineHeight: 1.45 } },
        "The search combines color, fit, construction, and item type. That is the kind of typed product search where returning the exact SKU early matters.",
      ),
    ),
    React.createElement(
      RailBlock,
      { title: "Probe Signal" },
      React.createElement(
        "div",
        { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 7 } },
        React.createElement(MiniStat, {
          label: "Hit@10",
          value: pct(metrics.typedHit10Hyper3),
          accent: true,
        }),
        React.createElement(MiniStat, {
          label: "CLIP",
          value: pct(metrics.typedHit10Clip),
        }),
      ),
      React.createElement(
        "div",
        { style: { color: colors.mutedText, fontSize: 10, lineHeight: 1.4 } },
        "Benchmark details stay below the demo so the ranked cards remain the main evidence.",
      ),
    ),
  );
}

function BenchmarkDetails({ typedMetricRows, imageMetricRows }) {
  return React.createElement(
    "details",
    {
      style: {
        border: `1px solid ${colors.border}`,
        borderRadius: 6,
        background: colors.cardBg,
        padding: 9,
      },
    },
    React.createElement(
      "summary",
      {
        style: {
          color: colors.strongText,
          fontSize: 12,
          fontWeight: 700,
          cursor: "pointer",
        },
      },
      "Benchmark Details",
    ),
    React.createElement(
      "div",
      { style: { display: "flex", flexDirection: "column", gap: 8, marginTop: 9 } },
      React.createElement(
        TextBlock,
        null,
        "Bottom reference only. The result strips above are the main demo; these numbers keep the probe traceable.",
      ),
      React.createElement(MetricGrid, { rows: typedMetricRows }),
      React.createElement(
        TextBlock,
        null,
        "Separate image-to-image check, shown only for context because it is not the typed shopper search task.",
      ),
      React.createElement(MetricGrid, { rows: imageMetricRows }),
    ),
  );
}

export default function FashionSearchComparisonPanel() {
  const selection = usePanelSelection();
  const samplesState = usePanelSamples();
  const commands = usePanelCommands();
  const panelProps = usePanelProps();
  const [panelError, setPanelError] = React.useState(null);
  const [loadingKey, setLoadingKey] = React.useState(null);
  const [selectedExampleId, setSelectedExampleId] = React.useState(() =>
    typeof panelProps.initialExampleId === "string" ? panelProps.initialExampleId : null,
  );
  const [contentWidth, setContentWidth] = React.useState(0);
  const resultsContentRef = React.useRef(null);
  const didPrimeEvidence = React.useRef(false);
  const evidenceRequestSeq = React.useRef(0);
  const latestEvidenceRequest = React.useRef(null);
  const mode = panelProps.mode === "summary" ? "summary" : panelProps.mode === "results" ? "results" : "full";

  const models = React.useMemo(() => normalizeModels(panelProps.models), [panelProps.models]);
  const inspectableModels = React.useMemo(() => models.filter((model) => model.layoutKey), [models]);
  const examples = Array.isArray(panelProps.examples) ? panelProps.examples : [];
  const metrics = panelProps.metrics || {};
  const selectedExample =
    examples.find((item) => item.id === selectedExampleId) || examples[0] || null;
  const compactLayout = contentWidth > 0 && contentWidth < 680;
  const spaciousLayout = contentWidth >= 900;
  const typedMetricRows = [
    { label: "Typed search Hit@1", hyper3: metrics.typedHit1Hyper3, clip: metrics.typedHit1Clip },
    { label: "Typed search Hit@10", hyper3: metrics.typedHit10Hyper3, clip: metrics.typedHit10Clip },
    {
      label: "Typed category P@10",
      hyper3: metrics.typedCategoryP10Hyper3,
      clip: metrics.typedCategoryP10Clip,
    },
    { label: "Typed search MRR", hyper3: metrics.typedMrrHyper3, clip: metrics.typedMrrClip, kind: "decimal" },
  ];
  const imageMetricRows = [
    { label: "Image-to-image mAP", hyper3: metrics.imageRetrievalMapHyper3, clip: metrics.imageRetrievalMapClip },
  ];

  React.useEffect(() => {
    const node = resultsContentRef.current;
    if (!node) return undefined;

    const updateWidth = () => setContentWidth(Math.round(node.getBoundingClientRect().width));
    updateWidth();

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", updateWidth);
      return () => window.removeEventListener("resize", updateWidth);
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      const width = entry?.contentRect?.width;
      if (typeof width === "number") {
        setContentWidth(Math.round(width));
      } else {
        updateWidth();
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [mode]);

  const selectSimilarityAnchor = React.useCallback(
    async (sampleId) => {
      if (!sampleId) return;
      await commands.setSelection([sampleId], {
        persist: false,
        source: "panel",
        clearLasso: false,
      });
    },
    [commands],
  );

  const loadEvidenceForSample = React.useCallback(
    async ({ sampleId, model, source = "fashion-demo:evidence", errorPrefix = "Could not load the sample evidence panel" }) => {
      if (!sampleId || !model?.layoutKey) return;
      const requestKey = `${sampleId}:${model.layoutKey}:${model.spaceKey || ""}`;
      const request = { sampleId, model, source, errorPrefix, requestKey };
      latestEvidenceRequest.current = request;
      const requestSeq = evidenceRequestSeq.current + 1;
      evidenceRequestSeq.current = requestSeq;

      try {
        await commands.setActiveLayout(model.layoutKey, { persist: false });
        if (requestSeq !== evidenceRequestSeq.current) return;

        await commands.showSimilar({
          sampleId,
          layoutKey: model.layoutKey,
          spaceKey: model.spaceKey,
          k: 10,
          source,
          focus: "samples",
          persist: false,
        });
        if (requestSeq !== evidenceRequestSeq.current) return;

        await selectSimilarityAnchor(sampleId);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        setPanelError(`${errorPrefix}: ${message}`);
      }
    },
    [commands, selectSimilarityAnchor],
  );

  const showExampleEvidence = React.useCallback(
    async (item, model, source = "fashion-demo:query") => {
      if (!item || !model?.layoutKey) return;
      await loadEvidenceForSample({
        sampleId: item.queryId,
        model,
        source,
        errorPrefix: "Could not load the sample evidence panel",
      });
    },
    [loadEvidenceForSample],
  );

  const chooseExample = React.useCallback(
    (exampleId) => {
      setSelectedExampleId(exampleId);
      const item = examples.find((entry) => entry.id === exampleId);
      const evidenceModel =
        models.find((model) => model.key === "clip" && model.layoutKey) ||
        models.find((model) => model.layoutKey);
      if (item && evidenceModel) {
        void showExampleEvidence(item, evidenceModel, "fashion-demo:query-picker");
      }
    },
    [examples, models, showExampleEvidence],
  );

  React.useEffect(() => {
    if (mode === "summary") return;
    if (didPrimeEvidence.current) return;
    if (!selectedExample) return;
    const evidenceModel =
      models.find((model) => model.key === "clip" && model.layoutKey) ||
      models.find((model) => model.layoutKey);
    if (!evidenceModel) return;
    didPrimeEvidence.current = true;

    void showExampleEvidence(selectedExample, evidenceModel, "fashion-demo:initial");
  }, [mode, models, selectedExample, showExampleEvidence]);

  const clearSelection = async () => {
    if (commands.setLabelFilter) commands.setLabelFilter(null);
    setPanelError(null);
    await commands.clearQueryContext({ persist: true });
  };

  const selectModelQuery = async (item, model) => {
    const key = `${item.queryId}:${model.key}`;
    setPanelError(null);
    if (!model.layoutKey) {
      await commands.setSelection([item.queryId], { persist: false, source: `fashion-target:${model.key}` });
      commands.focusPanel("grid");
      return;
    }
    setLoadingKey(key);
    try {
      await loadEvidenceForSample({
        sampleId: item.queryId,
        model,
        source: `fashion-demo:${model.key}`,
        errorPrefix: "Could not select target item",
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setPanelError(`Could not select target item: ${message}`);
    } finally {
      setLoadingKey(null);
    }
  };

  const selectRankedResult = async (result, model) => {
    const key = `${result.sampleId}:${model.key}:ranked-result`;
    setPanelError(null);
    if (!model.layoutKey) {
      await commands.setSelection([result.sampleId], {
        persist: false,
        source: `fashion-ranked-result:${model.key}`,
      });
      commands.focusPanel("grid");
      return;
    }
    setLoadingKey(key);
    try {
      await loadEvidenceForSample({
        sampleId: result.sampleId,
        model,
        source: `fashion-ranked-result:${model.key}`,
        errorPrefix: "Could not select ranked result",
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setPanelError(`Could not select ranked result: ${message}`);
    } finally {
      setLoadingKey(null);
    }
  };

  const toolbar =
    mode === "summary"
      ? null
      : React.createElement(PanelToolbar, {
          items: [
            { id: "dataset", label: "Data", value: "DeepFashion" },
            { id: "samples", label: "Items", value: String(samplesState.totalSamples ?? "-") },
            { id: "selected", label: "Selected", value: String(selection.selectedIds?.length ?? 0) },
          ],
          actions: React.createElement(PanelToolbarButton, { onClick: clearSelection }, "Reset"),
        });

  const summaryContent = React.createElement(
    "div",
    {
      style: {
        height: "100%",
        overflow: "auto",
        padding: 12,
        background: colors.panelBg,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      },
    },
    React.createElement(
      Section,
      { title: "Buyer Decision View" },
      React.createElement(
        TextBlock,
        null,
        "Business readout for the selected shopper query.",
      ),
      examples.length
        ? React.createElement(ExampleChooser, {
            examples,
            selectedId: selectedExample?.id,
            onSelect: chooseExample,
          })
        : null,
    ),
    React.createElement(BusinessRail, { item: selectedExample, metrics, fill: true }),
  );

  const resultsContent = React.createElement(
    "div",
    {
      ref: resultsContentRef,
      style: {
        height: "100%",
        overflow: "auto",
        padding: compactLayout ? 10 : 14,
        background: colors.panelBg,
      },
    },
    React.createElement(
      "div",
      {
        style: {
          width: "100%",
          margin: 0,
          display: "flex",
          gap: compactLayout ? 10 : 12,
          alignItems: "flex-start",
          justifyContent: "stretch",
          flexWrap: "wrap",
        },
      },
      React.createElement(
        "main",
        {
          style: {
            flex: "1 1 auto",
            width: "100%",
            maxWidth: "none",
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
            gap: compactLayout ? 12 : 14,
          },
        },
        React.createElement(
          Section,
          { title: "Pick A Shopper Query" },
          React.createElement(
            TextBlock,
            null,
            "Pick a typed product search and compare where each model ranks the exact item.",
          ),
          examples.length
            ? React.createElement(ExampleChooser, {
                examples,
                selectedId: selectedExample?.id,
                onSelect: chooseExample,
                compact: compactLayout,
              })
            : React.createElement(
                "div",
                { style: { color: colors.bodyText, fontSize: 12, lineHeight: 1.45 } },
                "Demo examples are not configured.",
              ),
          selectedExample && inspectableModels.length
            ? React.createElement(
                Section,
                { title: "Inspect Exact Target" },
                React.createElement(
                  TextBlock,
                  null,
                  `Load the same target product in Samples: ${selectedExample?.targetTitle || "target product"}.`,
                ),
                React.createElement(ExactTargetActions, {
                  item: selectedExample,
                  models: inspectableModels,
                  loadingKey,
                  onSelectQuery: selectModelQuery,
                  compact: compactLayout,
                }),
              )
            : null,
          selectedExample && models.length
            ? React.createElement(SearchResultComparison, {
                item: selectedExample,
                models,
                loadingKey,
                onSelectResult: selectRankedResult,
                compact: compactLayout,
                spacious: spaciousLayout,
              })
            : null,
        ),
        React.createElement(BenchmarkDetails, { typedMetricRows, imageMetricRows }),
        panelError
          ? React.createElement(
              "div",
              { style: { color: colors.error, fontSize: 11, lineHeight: 1.35 } },
              panelError,
            )
          : null,
      ),
      mode === "full" ? React.createElement(BusinessRail, { item: selectedExample, metrics }) : null,
    ),
  );

  return React.createElement(Panel, { className: "h-full" }, toolbar, mode === "summary" ? summaryContent : resultsContent);
}
