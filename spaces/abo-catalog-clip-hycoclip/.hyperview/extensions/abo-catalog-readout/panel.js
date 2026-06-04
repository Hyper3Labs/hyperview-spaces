const sdk = globalThis.HyperViewPanelSDK;
if (!sdk) throw new Error("HyperViewPanelSDK is not available on window.");

const { React, components, hooks } = sdk;
const { Panel, PanelToolbar, PanelToolbarButton } = components;
const {
  usePanelClient,
  usePanelDatasetInfo,
  usePanelSelection,
  usePanelSamples,
  usePanelCommands,
  usePanelProps,
} = hooks;

const DEFAULT_EXAMPLES = [
  {
    id: "lighting",
    title: "Lighting fixture",
    family: "Lighting",
    queryId: "B07HK5WXQP_510lSNJKiyL",
    queryLabel: "LIGHT_FIXTURE",
    summaries: {
      clip: { hits: 2, text: "Also returns earrings, home decor, bedding, kitchen, sandals." },
      candidate: { hits: 10, text: "Returns fixtures and lamps." },
    },
  },
  {
    id: "chandelier",
    title: "Chandelier-style fixture",
    family: "Lighting",
    queryId: "B07MF1RNWQ_51Vei4EHzBL",
    queryLabel: "LIGHT_FIXTURE",
    summaries: {
      clip: { hits: 2, text: "Also returns earrings, necklace-like jewelry, table." },
      candidate: { hits: 10, text: "Returns light fixtures first, then lamps." },
    },
  },
  {
    id: "footwear",
    title: "Sandal",
    family: "Footwear",
    queryId: "B07WHRRNQK_61_LTvw9qDL",
    queryLabel: "SANDAL",
    summaries: {
      clip: { hits: 6, text: "Also returns accessories, handbags." },
      candidate: { hits: 10, text: "Returns sandals with nearby shoes." },
    },
  },
];

const colors = {
  panelBg: "#111827",
  cardBg: "#161f2d",
  buttonBg: "#1f2937",
  border: "#334155",
  text: "#e5e7eb",
  strongText: "#f8fafc",
  mutedText: "#9ca3af",
  bodyText: "#cbd5e1",
  error: "#fca5a5",
};

function prettyLabel(label) {
  return String(label || "unlabeled").replaceAll("_", " ").toLowerCase();
}

function titleLabel(label) {
  return prettyLabel(label).replace(/\b\w/g, (char) => char.toUpperCase());
}

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
        padding: "7px 8px",
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
      spaceKey: model.spaceKey || model.space_key || null,
    }))
    .filter((model) => model.layoutKey);
}

function inferModels(datasetInfo) {
  const layouts = Array.isArray(datasetInfo?.layouts) ? datasetInfo.layouts : [];

  const clipLayout =
    layouts.find((layout) => String(layout.layout_key || layout.layoutKey || "").includes("openai_clip")) ||
    layouts.find((layout) => String(layout.geometry || "").toLowerCase() === "euclidean");
  const candidateLayout =
    layouts.find((layout) => String(layout.layout_key || layout.layoutKey || "").includes("hycoclip")) ||
    layouts.find((layout) => String(layout.geometry || "").toLowerCase() === "poincare");

  return [
    clipLayout && {
      key: "clip",
      displayName: "CLIP",
      buttonLabel: "CLIP query",
      layoutKey: clipLayout.layout_key || clipLayout.layoutKey,
      spaceKey: clipLayout.space_key || clipLayout.spaceKey,
    },
    candidateLayout && {
      key: "candidate",
      displayName: "HyCoCLIP",
      buttonLabel: "HyCoCLIP query",
      layoutKey: candidateLayout.layout_key || candidateLayout.layoutKey,
      spaceKey: candidateLayout.space_key || candidateLayout.spaceKey,
    },
  ].filter(Boolean);
}

function getSummary(item, modelKey) {
  return item.summaries?.[modelKey] || item.modelSummaries?.[modelKey] || {};
}

function ExampleCard({
  item,
  models,
  loadingKey,
  onSelectQuery,
}) {
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
      { style: { color: colors.strongText, fontSize: 13, fontWeight: 700 } },
      item.title,
    ),
    React.createElement(
      "div",
      { style: { color: colors.mutedText, fontSize: 11 } },
      `${item.family} query: ${titleLabel(item.queryLabel)}`,
    ),
    React.createElement(
      "div",
      { style: { display: "grid", gridTemplateColumns: gridColumns, gap: 8 } },
      models.map((model) => {
        const summary = getSummary(item, model.key);
        return React.createElement(
          "div",
          {
            key: model.key,
            style: {
              border: `1px solid ${colors.border}`,
              borderRadius: 4,
              padding: 8,
            },
          },
          React.createElement(
            "div",
            { style: { color: colors.strongText, fontSize: 12, fontWeight: 700, marginBottom: 4 } },
            `${model.displayName}: ${summary.hits ?? "-"} / 10 matching neighbors`,
          ),
          React.createElement(
            "div",
            { style: { color: colors.bodyText, fontSize: 11, lineHeight: 1.35 } },
            summary.text || "Open Samples to inspect this model's nearest products.",
          ),
        );
      }),
    ),
    React.createElement(
      "div",
      { style: { color: colors.mutedText, fontSize: 11, lineHeight: 1.35 } },
      "Both buttons select this same query. The Samples tab shows that model's neighbors.",
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
            title: `Select this query and show ${model.displayName} neighbors`,
          },
          loadingKey === choiceKey ? "Loading..." : model.buttonLabel,
        );
      }),
    ),
  );
}

export default function CatalogComparisonPanel() {
  const client = usePanelClient();
  const datasetInfo = usePanelDatasetInfo();
  const selection = usePanelSelection();
  const samplesState = usePanelSamples();
  const commands = usePanelCommands();
  const panelProps = usePanelProps();
  const [panelError, setPanelError] = React.useState(null);
  const [loadingKey, setLoadingKey] = React.useState(null);

  const models = React.useMemo(() => {
    const fromProps = normalizeModels(panelProps.models);
    return fromProps.length ? fromProps : inferModels(datasetInfo);
  }, [datasetInfo, panelProps.models]);
  const examples = Array.isArray(panelProps.examples) && panelProps.examples.length
    ? panelProps.examples
    : DEFAULT_EXAMPLES;
  const modelNames = React.useMemo(
    () => models.map((model) => model.displayName).join(" and "),
    [models],
  );

  const clearSelection = async () => {
    if (commands.setLabelFilter) commands.setLabelFilter(null);
    setPanelError(null);
    await commands.setSelection([]);
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
      const similar = await client.searchSimilar(item.queryId, {
        k: 10,
        spaceKey: model.spaceKey,
        layoutKey: model.layoutKey,
      });
      const neighborIds = Array.isArray(similar?.results)
        ? similar.results.map((sample) => sample.id).filter(Boolean)
        : [];
      await commands.setLayout(model.layoutKey);
      await commands.setSelection([item.queryId, ...neighborIds]);
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
        { id: "dataset", label: "Data", value: "ABO" },
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
          gap: 14,
          background: colors.panelBg,
        },
      },
      React.createElement(
        Section,
        { title: "What This Shows" },
        React.createElement(
          "div",
          { style: { color: colors.bodyText, fontSize: 12, lineHeight: 1.45 } },
          `Use the same query image under ${modelNames}. Samples opens to that model's nearest products.`,
        ),
      ),
      React.createElement(
        Section,
        { title: "Real Examples" },
        React.createElement(
          "div",
          { style: { display: "flex", flexDirection: "column", gap: 8 } },
          examples.map((item) =>
            React.createElement(ExampleCard, {
              key: item.id,
              item,
              models,
              loadingKey,
              onSelectQuery: selectModelQuery,
            }),
          ),
        ),
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
