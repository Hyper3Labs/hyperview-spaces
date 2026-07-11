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
  cardBgSoft: "#121b29",
  buttonBg: "#1f2937",
  border: "#334155",
  text: "#e5e7eb",
  strongText: "#f8fafc",
  mutedText: "#9ca3af",
  bodyText: "#cbd5e1",
  accent: "#34d399",
  accentSoft: "#0f3b2f",
  clip: "#93c5fd",
  candidate: "#34d399",
  faint: "#1e293b",
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
    { style: { display: "flex", flexDirection: "column", gap: 7 } },
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

function Walkthrough() {
  const steps = [
    ["Pick", "Start from a failing scene query."],
    ["Compare", "Show CLIP, then Hyper3-CLIP."],
    ["Audit", "Check exact scene and parent group."],
  ];

  return React.createElement(
    "div",
    {
      style: {
        display: "grid",
        gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
        gap: 6,
      },
    },
    steps.map(([label, text], index) =>
      React.createElement(
        "div",
        {
          key: label,
          style: {
            border: `1px solid ${colors.border}`,
            borderRadius: 4,
            background: colors.cardBgSoft,
            padding: "7px 8px",
            minHeight: 58,
          },
        },
        React.createElement(
          "div",
          { style: { color: colors.accent, fontSize: 11, fontWeight: 800, marginBottom: 3 } },
          `${index + 1}. ${label}`,
        ),
        React.createElement(
          "div",
          { style: { color: colors.bodyText, fontSize: 11, lineHeight: 1.3 } },
          text,
        ),
      ),
    ),
  );
}

function BusinessCase() {
  return React.createElement(
    "div",
    {
      style: {
        border: `1px solid ${colors.border}`,
        borderRadius: 4,
        background: colors.cardBg,
        padding: 10,
        display: "flex",
        flexDirection: "column",
        gap: 6,
      },
    },
    React.createElement(
      "div",
      { style: { color: colors.strongText, fontSize: 13, fontWeight: 800, lineHeight: 1.25 } },
      "Retrieval audit for aerial image libraries",
    ),
    React.createElement(
      "div",
      { style: { color: colors.bodyText, fontSize: 11, lineHeight: 1.35 } },
      "When an analyst asks for more scenes like this, the top results should stay in the right scene class and operational group. This demo shows where CLIP drifts and where Hyper3-CLIP keeps the neighborhood cleaner.",
    ),
  );
}

function BenchmarkTable({ benchmark }) {
  if (!benchmark || !Array.isArray(benchmark.rows)) return null;
  return React.createElement(
    "div",
    {
      style: {
        border: `1px solid ${colors.border}`,
        borderRadius: 4,
        background: colors.cardBg,
        overflow: "hidden",
      },
    },
    React.createElement(
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
          { style: { background: colors.cardBgSoft } },
          ["Metric", "CLIP", "Hyper3-CLIP", "Delta"].map((heading) =>
            React.createElement(
              "th",
              {
                key: heading,
                style: {
                  padding: "7px 8px",
                  borderBottom: `1px solid ${colors.border}`,
                  color: colors.mutedText,
                  fontSize: 10,
                  fontWeight: 700,
                  textAlign: heading === "Metric" ? "left" : "right",
                },
              },
              heading,
            ),
          ),
        ),
      ),
      React.createElement(
        "tbody",
        null,
        benchmark.rows.map((row) =>
          React.createElement(
            "tr",
            { key: row.metric },
            React.createElement(
              "td",
              { style: { padding: "7px 8px", borderBottom: `1px solid ${colors.faint}` } },
              row.metric,
            ),
            React.createElement(
              "td",
              {
                style: {
                  padding: "7px 8px",
                  borderBottom: `1px solid ${colors.faint}`,
                  textAlign: "right",
                  fontVariantNumeric: "tabular-nums",
                },
              },
              row.clip,
            ),
            React.createElement(
              "td",
              {
                style: {
                  padding: "7px 8px",
                  borderBottom: `1px solid ${colors.faint}`,
                  color: colors.strongText,
                  textAlign: "right",
                  fontVariantNumeric: "tabular-nums",
                },
              },
              row.hyper3,
            ),
            React.createElement(
              "td",
              {
                style: {
                  padding: "7px 8px",
                  borderBottom: `1px solid ${colors.faint}`,
                  color: colors.accent,
                  fontWeight: 800,
                  textAlign: "right",
                  fontVariantNumeric: "tabular-nums",
                },
              },
              row.delta,
            ),
          ),
        ),
      ),
    ),
    benchmark.caveat
      ? React.createElement(
          "div",
          { style: { color: colors.mutedText, fontSize: 10, lineHeight: 1.3, padding: "7px 8px" } },
          benchmark.caveat,
        )
      : null,
  );
}

function ModelCompareTable({ item, models, loadingKey, onSelectQuery }) {
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
        ["Model", "Same", "Parent", ""].map((heading, index) =>
          React.createElement(
            "th",
            {
              key: `${heading}-${index}`,
              style: {
                padding: "6px 0",
                borderBottom: `1px solid ${colors.border}`,
                color: colors.mutedText,
                fontSize: 10,
                fontWeight: 700,
                textAlign: index === 0 ? "left" : "right",
              },
            },
            heading,
          ),
        ),
      ),
    ),
    React.createElement(
      "tbody",
      null,
      models.map((model) => {
        const summary = getSummary(item, model.key);
        const choiceKey = `${item.queryId}:${model.key}`;
        return React.createElement(
          "tr",
          { key: model.key },
          React.createElement(
            "td",
            {
              style: {
                padding: "7px 0",
                borderBottom: `1px solid ${colors.faint}`,
                color: colors.strongText,
                fontWeight: 700,
              },
            },
            model.displayName.replace(" - ", " "),
          ),
          React.createElement(
            "td",
            {
              style: {
                padding: "7px 0",
                borderBottom: `1px solid ${colors.faint}`,
                textAlign: "right",
                fontVariantNumeric: "tabular-nums",
              },
            },
            `${summary.sameClassHits ?? "-"} / ${summary.total ?? 10}`,
          ),
          React.createElement(
            "td",
            {
              style: {
                padding: "7px 0",
                borderBottom: `1px solid ${colors.faint}`,
                textAlign: "right",
                fontVariantNumeric: "tabular-nums",
              },
            },
            `${summary.parentHits ?? "-"} / ${summary.total ?? 10}`,
          ),
          React.createElement(
            "td",
            { style: { padding: "7px 0", borderBottom: `1px solid ${colors.faint}`, textAlign: "right" } },
            React.createElement(
              Button,
              {
                onClick: () => onSelectQuery(item, model),
                disabled: loadingKey === choiceKey,
                title: `Select this query and show ${model.displayName} neighbors`,
                compact: true,
              },
              loadingKey === choiceKey ? "..." : model.key === "candidate" ? "Show" : "Show",
            ),
          ),
        );
      }),
    ),
  );
}

function Button({ children, onClick, title, disabled, compact }) {
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
        padding: compact ? "4px 7px" : "7px 8px",
        fontSize: compact ? 10 : 11,
        lineHeight: 1.2,
        cursor: disabled ? "default" : "pointer",
        textAlign: "center",
        opacity: disabled ? 0.65 : 1,
        whiteSpace: "nowrap",
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
    }))
    .filter((model) => model.layoutKey);
}

function getSummary(item, modelKey) {
  return item.summaries?.[modelKey] || item.modelSummaries?.[modelKey] || {};
}

function deltaLine(item) {
  const classDelta = typeof item.classDelta === "number" ? item.classDelta : 0;
  const parentDelta = typeof item.parentDelta === "number" ? item.parentDelta : 0;
  const color = classDelta > 0 || parentDelta > 0 ? colors.accent : colors.mutedText;
  return React.createElement(
    "div",
    {
      style: {
        color,
        background: classDelta > 0 || parentDelta > 0 ? colors.accentSoft : "transparent",
        border: `1px solid ${classDelta > 0 || parentDelta > 0 ? "#145a46" : colors.border}`,
        borderRadius: 999,
        padding: "4px 7px",
        fontSize: 11,
        fontWeight: 700,
        whiteSpace: "nowrap",
      },
    },
    `${classDelta >= 0 ? "+" : ""}${classDelta} same / ${parentDelta >= 0 ? "+" : ""}${parentDelta} parent`,
  );
}

function ExampleCard({
  item,
  models,
  loadingKey,
  onSelectQuery,
}) {
  return React.createElement(
    "div",
    {
      style: {
        border: `1px solid ${colors.border}`,
        borderRadius: 4,
        background: colors.cardBg,
        padding: 9,
        display: "flex",
        flexDirection: "column",
        gap: 7,
      },
    },
    React.createElement(
      "div",
      {
        style: {
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 8,
        },
      },
      React.createElement(
        "div",
        { style: { minWidth: 0 } },
        React.createElement(
          "div",
          { style: { color: colors.strongText, fontSize: 13, fontWeight: 800 } },
          item.title,
        ),
        React.createElement(
          "div",
          { style: { color: colors.mutedText, fontSize: 10, marginTop: 2 } },
          `${item.family} · ${titleLabel(item.queryLabel)}`,
        ),
      ),
      deltaLine(item),
    ),
    item.insight
      ? React.createElement(
          "div",
          {
            style: {
              color: colors.bodyText,
              fontSize: 11,
              lineHeight: 1.35,
              borderLeft: `2px solid ${colors.accent}`,
              paddingLeft: 8,
            },
          },
          item.insight,
        )
      : null,
    React.createElement(ModelCompareTable, { item, models, loadingKey, onSelectQuery }),
  );
}

export default function GeospatialComparisonPanel() {
  const selection = usePanelSelection();
  const samplesState = usePanelSamples();
  const commands = usePanelCommands();
  const panelProps = usePanelProps();
  const [panelError, setPanelError] = React.useState(null);
  const [loadingKey, setLoadingKey] = React.useState(null);

  const models = React.useMemo(() => normalizeModels(panelProps.models), [panelProps.models]);
  const examples = Array.isArray(panelProps.examples) ? panelProps.examples : [];
  const datasetLabel = String(panelProps.datasetLabel || "NWPU-RESISC45");
  const sampleCount = typeof panelProps.sampleCount === "number" ? panelProps.sampleCount : samplesState.totalSamples;
  const classCount = typeof panelProps.classCount === "number" ? panelProps.classCount : null;

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
      await commands.setActiveLayout(model.layoutKey, { persist: false });
      await commands.showSimilar({
        sampleId: item.queryId,
        layoutKey: model.layoutKey,
        k: 10,
        source: `geospatial-demo:${model.key}`,
        focus: "samples",
        persist: false,
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
        { id: "dataset", label: "Data", value: datasetLabel },
        {
          id: "samples",
          label: "Sample",
          value: classCount ? `${sampleCount} / ${classCount} classes` : String(sampleCount ?? "-"),
        },
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
          padding: 10,
          display: "flex",
          flexDirection: "column",
          gap: 12,
          background: colors.panelBg,
        },
      },
      React.createElement(
        Section,
        { title: "Business case" },
        React.createElement(BusinessCase, null),
      ),
      React.createElement(
        Section,
        { title: "What to do" },
        React.createElement(Walkthrough, null),
      ),
      React.createElement(
        Section,
        { title: "Queries to inspect" },
        examples.length && models.length
          ? React.createElement(
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
            )
          : React.createElement(
              "div",
              { style: { color: colors.bodyText, fontSize: 12, lineHeight: 1.45 } },
              "Demo examples are not configured.",
            ),
      ),
      panelError
        ? React.createElement(
            "div",
            { style: { color: colors.error, fontSize: 11, lineHeight: 1.35 } },
            panelError,
          )
        : null,
      React.createElement(
        Section,
        { title: "Benchmark context" },
        React.createElement(BenchmarkTable, { benchmark: panelProps.benchmark }),
      ),
    ),
  );
}
