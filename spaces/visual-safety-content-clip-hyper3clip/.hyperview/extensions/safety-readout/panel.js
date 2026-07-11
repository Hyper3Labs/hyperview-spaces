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
  panelBg: "#0f172a",
  cardBg: "#162032",
  buttonBg: "#233047",
  border: "#334155",
  text: "#e5e7eb",
  strongText: "#f8fafc",
  mutedText: "#94a3b8",
  bodyText: "#cbd5e1",
  accent: "#38bdf8",
  review: "#fbbf24",
  safe: "#34d399",
  error: "#fca5a5",
};

function normalizeModels(value) {
  if (!Array.isArray(value)) return [];
  return value
    .map((model, index) => ({
      key: String(model.key || `model-${index}`),
      displayName: String(model.displayName || model.display_name || model.key || `Model ${index + 1}`),
      buttonLabel: String(
        model.buttonLabel || model.button_label || `${model.displayName || model.key || "Model"} query`,
      ),
      layoutKey: model.layoutKey || model.layout_key || null,
    }))
    .filter((model) => model.layoutKey);
}

function titleLabel(label) {
  return String(label || "unlabeled")
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatMetric(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  return value.toFixed(3);
}

function Button({ children, onClick, title, disabled }) {
  return React.createElement(
    "button",
    {
      type: "button",
      onClick,
      title,
      disabled,
      style: {
        border: `1px solid ${colors.border}`,
        background: colors.buttonBg,
        color: colors.text,
        borderRadius: 4,
        padding: "8px 9px",
        fontSize: 11,
        lineHeight: 1.2,
        cursor: disabled ? "default" : "pointer",
        textAlign: "left",
        opacity: disabled ? 0.65 : 1,
      },
    },
    children,
  );
}

function SectionTitle({ children }) {
  return React.createElement(
    "h3",
    {
      style: {
        margin: 0,
        color: colors.strongText,
        fontSize: 13,
        fontWeight: 700,
      },
    },
    children,
  );
}

function Hero({ bucketCounts }) {
  return React.createElement(
    "div",
    {
      style: {
        border: `1px solid ${colors.border}`,
        borderRadius: 6,
        background: colors.cardBg,
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      },
    },
    React.createElement(
      "div",
      { style: { color: colors.accent, fontSize: 11, fontWeight: 700, textTransform: "uppercase" } },
      "Marketplace upload triage",
    ),
    React.createElement(
      "div",
      { style: { color: colors.strongText, fontSize: 15, fontWeight: 800, lineHeight: 1.25 } },
      "Classify each new listing as safe or needs review before it goes live.",
    ),
    React.createElement(
      "div",
      { style: { color: colors.bodyText, fontSize: 12, lineHeight: 1.45 } },
      "This public demo uses harmless Open Images examples to stand in for a marketplace upload stream: normal listings should pass, regulated or risky objects should enter the review queue.",
    ),
    React.createElement(
      "div",
      { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 } },
      React.createElement(StatChip, {
        label: "Safe",
        value: String(bucketCounts?.safe ?? 60),
        color: colors.safe,
      }),
      React.createElement(StatChip, {
        label: "Needs review",
        value: String(bucketCounts?.needs_review ?? 60),
        color: colors.review,
      }),
    ),
  );
}

function StatChip({ label, value, color }) {
  return React.createElement(
    "div",
    {
      style: {
        border: `1px solid ${colors.border}`,
        borderRadius: 4,
        padding: "7px 8px",
        background: "#101827",
      },
    },
    React.createElement("div", { style: { color, fontSize: 16, fontWeight: 800 } }, value),
    React.createElement("div", { style: { color: colors.mutedText, fontSize: 11 } }, label),
  );
}

function ScenarioCard({ item, models, loadingKey, onSelectQuery }) {
  const isReview = item.bucket === "needs_review";
  const chipColor = isReview ? colors.review : colors.safe;
  const gridColumns = models.length > 1 ? "repeat(2, minmax(0, 1fr))" : "1fr";

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
        gap: 8,
      },
    },
    React.createElement(
      "div",
      { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 } },
      React.createElement(
        "div",
        { style: { display: "flex", alignItems: "center", gap: 8 } },
        React.createElement(
          "div",
          {
            style: {
              width: 22,
              height: 22,
              borderRadius: 4,
              border: `1px solid ${colors.border}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: colors.accent,
              fontSize: 12,
              fontWeight: 800,
            },
          },
          item.step || "?",
        ),
        React.createElement(
          "div",
          { style: { color: colors.strongText, fontSize: 13, fontWeight: 800 } },
          item.title,
        ),
      ),
      React.createElement(
        "div",
        {
          style: {
            border: `1px solid ${chipColor}`,
            color: chipColor,
            borderRadius: 4,
            padding: "2px 5px",
            fontSize: 10,
            whiteSpace: "nowrap",
          },
        },
        item.family,
      ),
    ),
    React.createElement(
      "div",
      {
        style: {
          display: "grid",
          gridTemplateColumns: "74px 1fr",
          gap: 8,
          color: colors.bodyText,
          fontSize: 11,
          lineHeight: 1.35,
        },
      },
      React.createElement("div", { style: { color: colors.accent, fontWeight: 700 } }, "Decision"),
      React.createElement("div", null, item.decision),
      React.createElement("div", { style: { color: colors.accent, fontWeight: 700 } }, "Value"),
      React.createElement("div", null, item.businessValue),
      React.createElement("div", { style: { color: colors.accent, fontWeight: 700 } }, "Inspect"),
      React.createElement("div", null, item.inspect),
    ),
    React.createElement(
      "div",
      { style: { color: colors.mutedText, fontSize: 10, lineHeight: 1.3 } },
      `Dataset labels: ${(item.labels || []).map(titleLabel).join(", ")}`,
    ),
    React.createElement(
      "div",
      { style: { display: "grid", gridTemplateColumns: gridColumns, gap: 6 } },
      models.map((model) => {
        const choiceKey = `${item.queryId}:${model.key}`;
        return React.createElement(
          Button,
          {
            key: model.key,
            onClick: () => onSelectQuery(item, model),
            disabled: loadingKey === choiceKey,
            title: `Show ${model.displayName} neighbors for this upload`,
          },
          loadingKey === choiceKey ? "Loading..." : model.buttonLabel,
        );
      }),
    ),
  );
}

function MetricTable({ metrics }) {
  const rows = [
    ["Accuracy", "accuracy"],
    ["AUROC", "auroc"],
    ["AP, review class", "apReview"],
    ["F1, review class", "f1Review"],
    ["Review recall", "reviewRecall"],
    ["Review precision", "reviewPrecision"],
    ["Safe recall", "safeRecall"],
  ];

  return React.createElement(
    "table",
    {
      style: {
        width: "100%",
        borderCollapse: "collapse",
        color: colors.bodyText,
        fontSize: 11,
      },
    },
    React.createElement(
      "thead",
      null,
      React.createElement(
        "tr",
        null,
        ["Metric", "CLIP", "hyper3-clip"].map((header) =>
          React.createElement(
            "th",
            {
              key: header,
              style: {
                padding: "6px 8px",
                textAlign: header === "Metric" ? "left" : "right",
                color: colors.strongText,
                borderBottom: `1px solid ${colors.border}`,
              },
            },
            header,
          ),
        ),
      ),
    ),
    React.createElement(
      "tbody",
      null,
      rows.map(([label, key]) =>
        React.createElement(
          "tr",
          { key },
          React.createElement("td", { style: { padding: "5px 8px" } }, label),
          React.createElement(
            "td",
            { style: { padding: "5px 8px", textAlign: "right" } },
            formatMetric(metrics?.clip?.[key]),
          ),
          React.createElement(
            "td",
            { style: { padding: "5px 8px", textAlign: "right" } },
            formatMetric(metrics?.candidate?.[key]),
          ),
        ),
      ),
    ),
  );
}

function Details({ title, children }) {
  return React.createElement(
    "details",
    {
      style: {
        border: `1px solid ${colors.border}`,
        borderRadius: 6,
        background: colors.cardBg,
        padding: 10,
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
      title,
    ),
    React.createElement(
      "div",
      { style: { marginTop: 8, display: "flex", flexDirection: "column", gap: 8 } },
      children,
    ),
  );
}

export default function SafetyComparisonPanel() {
  const selection = usePanelSelection();
  const samplesState = usePanelSamples();
  const commands = usePanelCommands();
  const panelProps = usePanelProps();
  const didRequestInitialReset = React.useRef(false);
  const [panelError, setPanelError] = React.useState(null);
  const [loadingKey, setLoadingKey] = React.useState(null);

  const models = React.useMemo(() => normalizeModels(panelProps.models), [panelProps.models]);
  const examples = Array.isArray(panelProps.examples) ? panelProps.examples : [];
  const metrics = panelProps.metrics || {};
  const bucketCounts = panelProps.bucketCounts || {};

  React.useEffect(() => {
    if (!models.length) return undefined;
    const resetKey = "openimages-safety-demo:initial-reset:v5";
    const storage = typeof window !== "undefined" ? window.sessionStorage : null;
    if (didRequestInitialReset.current || storage?.getItem(resetKey) === "1") {
      return undefined;
    }
    didRequestInitialReset.current = true;

    let cancelled = false;
    const resetInitialState = async () => {
      try {
        if (commands.setLabelFilter) commands.setLabelFilter(null);
        await commands.clearQueryContext({ persist: true });
        if (!cancelled) storage?.setItem(resetKey, "1");
      } catch (error) {
        didRequestInitialReset.current = false;
        if (!cancelled) console.warn("Could not reset Open Images safety demo state:", error);
      }
    };

    const timers = [0, 900, 2200].map((delay) => window.setTimeout(resetInitialState, delay));
    return () => {
      cancelled = true;
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [commands, models.length]);

  const clearSelection = async () => {
    if (commands.setLabelFilter) commands.setLabelFilter(null);
    setPanelError(null);
    await commands.clearQueryContext({ persist: true });
  };

  const selectModelQuery = async (item, model) => {
    const key = `${item.queryId}:${model.key}`;
    setPanelError(null);

    if (!model.layoutKey) {
      setPanelError(`${model.displayName} layout is not ready yet. Try again in a moment.`);
      return;
    }

    setLoadingKey(key);
    try {
      await commands.setActiveLayout(model.layoutKey);
      await commands.showSimilar({
        sampleId: item.queryId,
        layoutKey: model.layoutKey,
        k: 10,
        source: `openimages-safety-demo:${model.key}`,
        focus: "samples",
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setPanelError(`Could not select query: ${message}`);
    } finally {
      setLoadingKey(null);
    }
  };

  return React.createElement(
    Panel,
    { className: "h-full" },
    React.createElement(PanelToolbar, {
      items: [
        { id: "dataset", label: "Data", value: "Open Images" },
        { id: "samples", label: "Items", value: String(samplesState.totalSamples ?? "-") },
        { id: "selected", label: "Selected", value: String(selection.selectedIds?.length ?? 0) },
      ],
      actions: React.createElement(PanelToolbarButton, { onClick: clearSelection }, "Reset"),
    }),
    React.createElement(
      "div",
      {
        style: {
          height: "100%",
          overflow: "auto",
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 12,
          background: colors.panelBg,
        },
      },
      React.createElement(Hero, { bucketCounts }),
      React.createElement(
        "section",
        { style: { display: "flex", flexDirection: "column", gap: 8 } },
        React.createElement(SectionTitle, null, "Three upload decisions"),
        examples.length && models.length
          ? examples.map((item) =>
              React.createElement(ScenarioCard, {
                key: item.id,
                item,
                models,
                loadingKey,
                onSelectQuery: selectModelQuery,
              }),
            )
          : React.createElement(
              "div",
              { style: { color: colors.bodyText, fontSize: 12, lineHeight: 1.45 } },
              "Demo scenarios are not configured.",
            ),
      ),
      React.createElement(
        Details,
        { title: "Benchmark details" },
        React.createElement(
          "div",
          { style: { color: colors.bodyText, fontSize: 11, lineHeight: 1.4 } },
          `${metrics.dataset || "Open Images proxy"}: ${metrics.classBalance || ""}. ${metrics.readout || ""}`,
        ),
        React.createElement(MetricTable, { metrics }),
      ),
      panelError
        ? React.createElement(
            "div",
            { style: { color: colors.error, fontSize: 11, lineHeight: 1.35 } },
            panelError,
          )
        : null,
    ),
  );
}
