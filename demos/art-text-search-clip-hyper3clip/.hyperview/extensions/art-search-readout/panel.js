const sdk = globalThis.HyperViewPanelSDK;
if (!sdk || sdk.version !== "2") {
  throw new Error("HyperViewPanelSDK v2 is not available on window.");
}

const { React, components = {}, hooks = {} } = sdk;
const Panel = components.Panel || (({ children, className = "" }) => (
  <div className={.trim()} style={{ height: "100%" }}>
    {children}
  </div>
));
const {
  useActiveLayout,
  useCommandClient,
  usePanelState,
  useSampleResults,
  useSelection,
} = hooks;

const colors = {
  panelBg: "#111827",
  cardBg: "#16202e",
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

function normalizeModels(value) {
  if (!Array.isArray(value)) return [];
  return value.map((model, index) => ({
    key: String(model.key || `model-${index}`),
    displayName: String(model.displayName || model.display_name || model.key || `Model ${index + 1}`),
    buttonLabel: String(model.buttonLabel || model.button_label || `Inspect ${model.displayName || "model"}`),
    layoutKey: model.layoutKey || model.layout_key || null,
    spaceKey: model.spaceKey || model.space_key || null,
  }));
}

function modelBorder(model) {
  return model.key === "candidate" ? "#3f6f5b" : colors.border;
}

function modelAccent(model) {
  return model.key === "candidate" ? colors.success : colors.bodyText;
}

function Section({ title, children }) {
  return React.createElement(
    "section",
    { style: { display: "flex", flexDirection: "column", gap: 8 } },
    React.createElement(
      "h3",
      { style: { margin: 0, color: colors.strongText, fontSize: 13, fontWeight: 700 } },
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

function QueryChooser({ examples, selectedId, onSelect, compact = false }) {
  return React.createElement(
    "div",
    {
      style: {
        display: "grid",
        gridTemplateColumns: compact ? "1fr" : "repeat(auto-fit, minmax(180px, 1fr))",
        gap: 7,
      },
    },
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
            padding: "8px 9px",
            textAlign: "left",
            cursor: "pointer",
            minHeight: 74,
          },
        },
        React.createElement(
          "div",
          { style: { color: colors.strongText, fontSize: 12, fontWeight: 700, marginBottom: 3 } },
          item.title,
        ),
        React.createElement(
          "div",
          {
            style: {
              color: colors.bodyText,
              fontSize: 11,
              lineHeight: 1.35,
              overflow: "hidden",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
            },
          },
          item.query,
        ),
        React.createElement(
          "div",
          { style: { color: colors.mutedText, fontSize: 9, marginTop: 5, textTransform: "uppercase" } },
          item.family || "composition",
        ),
      );
    }),
  );
}

function ModelButtons({ item, models, loadingKey, onInspect, compact = false }) {
  return React.createElement(
    "div",
    { style: { display: "grid", gridTemplateColumns: compact ? "1fr" : "1fr 1fr", gap: 8 } },
    models.map((model) => {
      const key = `${item?.queryId || "none"}:${model.key}`;
      return React.createElement(
        "button",
        {
          key: model.key,
          type: "button",
          onClick: () => onInspect(item, model),
          disabled: !item || loadingKey === key,
          style: {
            border: `1px solid ${modelBorder(model)}`,
            borderRadius: 5,
            padding: 9,
            background: model.key === "candidate" ? "rgba(134, 239, 172, 0.06)" : "#0f172a",
            color: colors.text,
            textAlign: "left",
            cursor: !item || loadingKey === key ? "default" : "pointer",
            opacity: !item || loadingKey === key ? 0.65 : 1,
          },
        },
        React.createElement(
          "div",
          { style: { color: colors.strongText, fontSize: 12, fontWeight: 700, marginBottom: 4 } },
          model.displayName,
        ),
        React.createElement(
          "div",
          { style: { color: modelAccent(model), fontSize: 11, lineHeight: 1.35 } },
          loadingKey === key ? "Loading neighborhood..." : model.buttonLabel,
        ),
      );
    }),
  );
}

function QueryDetail({ item, onCopy, copied }) {
  if (!item) return null;
  return React.createElement(
    "div",
    {
      style: {
        border: `1px solid ${colors.border}`,
        borderRadius: 6,
        background: "#0f172a",
        padding: 10,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      },
    },
    React.createElement(
      "div",
      { style: { color: colors.mutedText, fontSize: 10, fontWeight: 700, textTransform: "uppercase" } },
      "Buyer Query",
    ),
    React.createElement(
      "div",
      { style: { color: colors.strongText, fontSize: 18, fontWeight: 800, lineHeight: 1.2 } },
      item.query,
    ),
    React.createElement(
      "div",
      { style: { color: colors.bodyText, fontSize: 11, lineHeight: 1.45 } },
      `Anchor work for map context: ${item.anchorTitle || "untitled"} by ${item.anchorArtist || "unknown artist"}.`,
    ),
    React.createElement(
      "div",
      { style: { display: "flex", flexWrap: "wrap", gap: 6 } },
      [item.anchorGenre, item.anchorStyle].filter(Boolean).map((value) =>
        React.createElement(
          "span",
          {
            key: value,
            style: {
              border: `1px solid ${colors.border}`,
              borderRadius: 999,
              color: colors.bodyText,
              fontSize: 10,
              padding: "3px 7px",
            },
          },
          value,
        ),
      ),
    ),
    React.createElement(
      "button",
      {
        type: "button",
        onClick: () => onCopy(item.query),
        style: {
          alignSelf: "flex-start",
          border: `1px solid ${colors.accent}`,
          borderRadius: 5,
          background: colors.buttonBg,
          color: colors.strongText,
          padding: "7px 10px",
          cursor: "pointer",
          fontSize: 12,
          fontWeight: 700,
        },
      },
      copied ? "Copied" : "Copy query",
    ),
  );
}

export default function ArtSearchComparisonPanel() {
  const { props: panelProps = {} } = usePanelState();
  const { selectedIds, setSelection } = useSelection();
  const { resetResults } = useSampleResults();
  const { setActiveLayout } = useActiveLayout();
  const { runCommand } = useCommandClient();
  const [panelError, setPanelError] = React.useState(null);
  const [loadingKey, setLoadingKey] = React.useState(null);
  const [copied, setCopied] = React.useState(false);
  const [selectedExampleId, setSelectedExampleId] = React.useState(() =>
    typeof panelProps.initialExampleId === "string" ? panelProps.initialExampleId : null,
  );
  const [contentWidth, setContentWidth] = React.useState(0);
  const contentRef = React.useRef(null);

  const models = React.useMemo(() => normalizeModels(panelProps.models), [panelProps.models]);
  const examples = Array.isArray(panelProps.examples) ? panelProps.examples : [];
  const selectedExample = examples.find((item) => item.id === selectedExampleId) || examples[0] || null;
  const compactLayout = contentWidth > 0 && contentWidth < 680;

  React.useEffect(() => {
    const node = contentRef.current;
    if (!node) return undefined;
    const updateWidth = () => setContentWidth(Math.round(node.getBoundingClientRect().width));
    updateWidth();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", updateWidth);
      return () => window.removeEventListener("resize", updateWidth);
    }
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect?.width;
      setContentWidth(typeof width === "number" ? Math.round(width) : 0);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const chooseExample = React.useCallback(
    async (exampleId) => {
      setSelectedExampleId(exampleId);
      setPanelError(null);
      const item = examples.find((entry) => entry.id === exampleId);
      if (item?.queryId) {
        await setSelection([item.queryId]);
      }
    },
    [examples, setSelection],
  );

  const inspectModel = async (item, model) => {
    if (!item?.queryId) return;
    const key = `${item.queryId}:${model.key}`;
    setPanelError(null);
    setLoadingKey(key);
    try {
      if (model.layoutKey) {
        await setActiveLayout(model.layoutKey);
        await runCommand("collection.neighbors.create", {
          args: {
            sample_id: item.queryId,
            layout_key: model.layoutKey,
            space_key: model.spaceKey,
            k: 10,
            source: `art-query-gallery:${model.key}`,
          },
        });
      }
      await setSelection([item.queryId]);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setPanelError(`Could not inspect artwork neighborhood: ${message}`);
    } finally {
      setLoadingKey(null);
    }
  };

  const copyQuery = async (query) => {
    setCopied(false);
    setPanelError(null);
    try {
      await navigator.clipboard.writeText(query);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setPanelError(`Could not copy query: ${message}`);
    }
  };

  const clearSelection = async () => {
    setPanelError(null);
    await resetResults({ focus: false, source: "art-query-gallery:reset" });
  };

  return React.createElement(
    Panel,
    null,
    React.createElement(
      "header",
      {
        style: {
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "8px 12px",
          borderBottom: `1px solid ${colors.border}`,
          background: colors.panelBg,
          color: colors.bodyText,
          fontSize: 10,
        },
      },
      React.createElement("strong", { style: { color: colors.strongText, fontSize: 12 } }, "Artwork Search Readout"),
      React.createElement("span", null, String(panelProps.datasetName || "Art")),
      React.createElement("span", null, `${panelProps.sampleCount ?? "-"} items`),
      React.createElement("span", null, `${selectedIds.length} selected`),
      React.createElement(
        "button",
        {
          type: "button",
          onClick: clearSelection,
          style: {
            marginLeft: "auto",
            border: `1px solid ${colors.border}`,
            borderRadius: 5,
            background: colors.buttonBg,
            color: colors.strongText,
            padding: "4px 8px",
            cursor: "pointer",
          },
        },
        "Reset",
      ),
    ),
    React.createElement(
      "div",
      {
        ref: contentRef,
        style: {
          flex: 1,
          minHeight: 0,
          overflow: "auto",
          padding: compactLayout ? 10 : 14,
          background: colors.panelBg,
          color: colors.text,
          display: "flex",
          flexDirection: "column",
          gap: compactLayout ? 12 : 14,
        },
      },
      panelError
        ? React.createElement(
            "div",
            {
              style: {
                border: `1px solid ${colors.error}`,
                borderRadius: 5,
                background: "rgba(252, 165, 165, 0.08)",
                color: colors.error,
                padding: 8,
                fontSize: 12,
              },
            },
            panelError,
          )
        : null,
      React.createElement(
        Section,
        { title: "Compositional Query Gallery" },
        React.createElement(
          TextBlock,
          null,
          "Marketplace artwork search fails when a title omits visible content. These prompts combine object, attribute, and setting so the image has to carry the match.",
        ),
        examples.length
          ? React.createElement(QueryChooser, {
              examples,
              selectedId: selectedExample?.id,
              onSelect: chooseExample,
              compact: compactLayout,
            })
          : React.createElement(TextBlock, null, "Demo examples are not configured."),
      ),
      selectedExample
        ? React.createElement(
            Section,
            { title: "Run The Buyer Prompt" },
            React.createElement(QueryDetail, {
              item: selectedExample,
              onCopy: copyQuery,
              copied,
            }),
          )
        : null,
      selectedExample && models.length
        ? React.createElement(
            Section,
            { title: "Inspect Map Context" },
            React.createElement(
              TextBlock,
              null,
              "Use the same prompt in HyperView text search, then compare the selected result and nearby paintings in each model layout.",
            ),
            React.createElement(ModelButtons, {
              item: selectedExample,
              models,
              loadingKey,
              onInspect: inspectModel,
              compact: compactLayout,
            }),
          )
        : null,
      React.createElement(
        Section,
        { title: "Dataset Note" },
        React.createElement(TextBlock, null, panelProps.licenseNote || ""),
      ),
    ),
  );
}
