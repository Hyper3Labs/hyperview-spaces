const sdk = globalThis.HyperViewPanelSDK;
if (!sdk) throw new Error("HyperViewPanelSDK is not available on window.");

const { React, components, hooks } = sdk;
const { Panel, PanelToolbar, PanelToolbarButton } = components;
const {
  usePanelClient,
  usePanelSelection,
  usePanelSamples,
  usePanelCommands,
  usePanelProps,
} = hooks;
const h = React.createElement;

const colors = {
  panelBg: "#0f1720",
  cardBg: "#151e2b",
  cardSoft: "#111827",
  buttonBg: "#1f2937",
  border: "#334155",
  borderSoft: "#243142",
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
  return value
    .map((model, index) => ({
      key: String(model.key || `model-${index}`),
      displayName: String(model.displayName || model.display_name || model.key || `Model ${index + 1}`),
      layoutKey: model.layoutKey || model.layout_key || null,
    }))
    .filter((model) => model.layoutKey);
}

function getSummary(item, modelKey) {
  return item.summaries?.[modelKey] || item.modelSummaries?.[modelKey] || {};
}

function rankLabel(summary) {
  if (summary.rank === 0 || summary.rank) return `#${summary.rank}`;
  return "-";
}

function titleLabel(label) {
  return String(label || "unlabeled")
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function compactTitle(value, limit = 58) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  return `${text.slice(0, Math.max(0, limit - 1)).trim()}...`;
}

function sampleTitle(sample, defaultTitle) {
  return (
    sample?.metadata?.title ||
    sample?.metadata?.product_title ||
    defaultTitle ||
    sample?.filename ||
    sample?.id ||
    "sample"
  );
}

function sampleMediaSrc(sample) {
  if (!sample) return null;
  if (sample.thumbnail) return `data:image/jpeg;base64,${sample.thumbnail}`;
  const mediaUrl = sample.media_url;
  if (!mediaUrl) return null;
  if (/^https?:\/\//.test(mediaUrl)) return mediaUrl;
  return new URL(mediaUrl, window.location.origin).toString();
}

function unique(values) {
  return Array.from(new Set(values.filter(Boolean)));
}

function resultRows(item, modelKey) {
  const rows = item.results?.[modelKey] || [];
  return Array.isArray(rows) ? rows : [];
}

function proofSampleIds(item) {
  const ids = [item?.targetSampleId];
  for (const rows of Object.values(item?.results || {})) {
    for (const row of rows || []) ids.push(row.id);
  }
  return unique(ids);
}

function SectionTitle({ step, title, action }) {
  return h(
    "div",
    {
      style: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 8,
      },
    },
    h(
      "div",
      { style: { display: "flex", alignItems: "center", gap: 7 } },
      h(
        "span",
        {
          style: {
            width: 20,
            height: 20,
            borderRadius: 999,
            border: `1px solid ${colors.border}`,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            color: colors.accent,
            fontSize: 11,
            fontWeight: 700,
          },
        },
        step,
      ),
      h(
        "h3",
        {
          style: {
            margin: 0,
            color: colors.strongText,
            fontSize: 12,
            fontWeight: 800,
            letterSpacing: 0.1,
          },
        },
        title,
      ),
    ),
    action || null,
  );
}

function MiniButton({ active, children, onClick, title }) {
  return h(
    "button",
    {
      type: "button",
      onClick,
      title,
      style: {
        border: `1px solid ${active ? colors.accent : colors.borderSoft}`,
        background: active ? "rgba(147, 197, 253, 0.12)" : colors.buttonBg,
        color: active ? colors.strongText : colors.bodyText,
        borderRadius: 5,
        padding: "6px 7px",
        fontSize: 11,
        lineHeight: 1.2,
        cursor: "pointer",
        textAlign: "left",
      },
    },
    children,
  );
}

function QueryButton({ item, active, models, onClick }) {
  const clip = getSummary(item, "clip");
  const candidate = getSummary(item, "candidate");
  return h(
    "button",
    {
      type: "button",
      onClick,
      style: {
        border: `1px solid ${active ? colors.accent : colors.borderSoft}`,
        background: active ? "rgba(147, 197, 253, 0.1)" : colors.cardBg,
        borderRadius: 6,
        padding: 9,
        color: colors.text,
        display: "flex",
        flexDirection: "column",
        gap: 5,
        cursor: "pointer",
        textAlign: "left",
      },
    },
    h(
      "div",
      { style: { display: "flex", justifyContent: "space-between", gap: 8 } },
      h("span", { style: { color: colors.strongText, fontSize: 12, fontWeight: 800 } }, item.title),
      h(
        "span",
        { style: { color: colors.accent, fontSize: 10, whiteSpace: "nowrap" } },
        `${models.find((m) => m.key === "candidate")?.displayName || "Hyper3"} ${rankLabel(candidate)}`,
      ),
    ),
    h(
      "div",
      { style: { color: colors.mutedText, fontSize: 11, lineHeight: 1.3 } },
      `${item.family} · CLIP ${rankLabel(clip)}`,
    ),
  );
}

function ResultTile({ row, sample, targetId, onOpen }) {
  const isTarget = row.target || row.id === targetId;
  const src = sampleMediaSrc(sample);
  const label = sample?.label || row.label || "";
  const title = sampleTitle(sample, row.title);
  return h(
    "button",
    {
      type: "button",
      title,
      onClick: onOpen,
      style: {
        position: "relative",
        minWidth: 76,
        width: 76,
        height: 104,
        border: `1px solid ${isTarget ? colors.success : colors.borderSoft}`,
        borderRadius: 5,
        overflow: "hidden",
        background: "#0b111a",
        boxShadow: isTarget ? "0 0 0 1px rgba(134, 239, 172, 0.25) inset" : "none",
        cursor: "pointer",
        padding: 0,
        textAlign: "left",
      },
    },
    h(
      "div",
      {
        style: {
          position: "absolute",
          top: 4,
          left: 4,
          zIndex: 2,
          borderRadius: 4,
          background: isTarget ? "#16a34a" : "rgba(15, 23, 32, 0.88)",
          color: "white",
          fontSize: 10,
          fontWeight: 800,
          padding: "2px 4px",
        },
      },
      `#${row.rank}`,
    ),
    isTarget
      ? h(
          "div",
          {
            style: {
              position: "absolute",
              top: 4,
              right: 4,
              zIndex: 2,
              borderRadius: 4,
              background: "rgba(22, 163, 74, 0.95)",
              color: "white",
              fontSize: 8,
              fontWeight: 900,
              padding: "2px 4px",
            },
          },
          "TARGET",
        )
      : null,
    src
      ? h("img", {
          src,
          alt: title,
          loading: "lazy",
          style: {
            display: "block",
            width: "100%",
            height: 78,
            objectFit: "contain",
            background: "white",
          },
        })
      : h(
          "div",
          {
            style: {
              height: 78,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: colors.mutedText,
              fontSize: 10,
              padding: 6,
              textAlign: "center",
            },
          },
          "loading",
        ),
    h(
      "div",
      {
        style: {
          height: 26,
          padding: "3px 4px",
          color: colors.bodyText,
          fontSize: 9,
          lineHeight: 1.15,
          overflow: "hidden",
          background: isTarget ? "rgba(22, 101, 52, 0.38)" : "rgba(15, 23, 32, 0.95)",
        },
      },
      label ? titleLabel(label) : compactTitle(title, 20),
    ),
  );
}

function ResultStrip({
  item,
  model,
  samplesById,
  loadingSamples,
  onInspectResults,
  onInspectTarget,
  onSelectResult,
}) {
  const summary = getSummary(item, model.key);
  const rows = resultRows(item, model.key);
  const hasTargetInTop = rows.some((row) => row.id === item.targetSampleId || row.target);
  const isCandidate = model.key === "candidate";

  return h(
    "div",
    {
      style: {
        border: `1px solid ${isCandidate ? "#315d4a" : colors.borderSoft}`,
        background: isCandidate ? "rgba(22, 101, 52, 0.12)" : colors.cardBg,
        borderRadius: 7,
        padding: 9,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      },
    },
    h(
      "div",
      { style: { display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" } },
      h(
        "div",
        null,
        h(
          "div",
          { style: { color: colors.strongText, fontSize: 12, fontWeight: 800 } },
          `${model.displayName}: target ${rankLabel(summary)}`,
        ),
        h(
          "div",
          { style: { color: isCandidate ? colors.success : colors.mutedText, fontSize: 10, marginTop: 2 } },
          hasTargetInTop ? "target visible in top 6" : "target not visible in top 6",
        ),
      ),
      h(
        "div",
        { style: { display: "flex", gap: 5 } },
        h(
          MiniButton,
          {
            onClick: () => onInspectResults(item, model),
            title: "Select these returned products in Samples",
          },
          "show top 6",
        ),
        h(
          MiniButton,
          {
            onClick: () => onInspectTarget(item, model),
            title: "Select the exact target listing",
          },
          "target",
        ),
      ),
    ),
    h(
      "div",
      {
        style: {
          display: "flex",
          gap: 6,
          overflowX: "auto",
          paddingBottom: 2,
        },
      },
      loadingSamples
        ? h(
            "div",
            { style: { color: colors.mutedText, fontSize: 11, padding: "8px 0" } },
            "Loading returned samples...",
          )
        : rows.map((row) =>
            h(ResultTile, {
              key: row.id,
              row,
              sample: samplesById[row.id],
              targetId: item.targetSampleId,
              onOpen: () => onSelectResult(model, row),
            }),
          ),
    ),
    h(
      "div",
      { style: { color: colors.bodyText, fontSize: 10, lineHeight: 1.35 } },
      summary.text || "Ranked by the precomputed ABO text-to-image probe.",
    ),
  );
}

function TextQueryFlow({
  proofs,
  models,
  activeProof,
  onPickProof,
  samplesById,
  loadingSamples,
  onInspectResults,
  onInspectTarget,
  onSelectResult,
}) {
  const orderedModels = [
    ...models.filter((model) => model.key === "candidate"),
    ...models.filter((model) => model.key !== "candidate"),
  ];

  if (!activeProof) {
    return h(
      "div",
      { style: { color: colors.bodyText, fontSize: 12 } },
      "No text-query examples are configured.",
    );
  }

  return h(
    "div",
    { style: { display: "flex", flexDirection: "column", gap: 12 } },
    h(SectionTitle, { step: "1", title: "Pick a predefined text query" }),
    h(
      "div",
      { style: { display: "grid", gridTemplateColumns: "1fr", gap: 6 } },
      proofs.map((item) =>
        h(QueryButton, {
          key: item.id,
          item,
          models,
          active: activeProof.id === item.id,
          onClick: () => onPickProof(item),
        }),
      ),
    ),
    h(SectionTitle, { step: "2", title: "Compare exact-target rank" }),
    h(
      "div",
      {
        style: {
          border: `1px solid ${colors.borderSoft}`,
          background: colors.cardSoft,
          borderRadius: 7,
          padding: 9,
          display: "flex",
          flexDirection: "column",
          gap: 7,
        },
      },
      h(
        "div",
        { style: { color: colors.strongText, fontSize: 12, fontWeight: 800 } },
        activeProof.targetTitle || activeProof.title,
      ),
      h(
        "div",
        { style: { color: colors.bodyText, fontSize: 11, lineHeight: 1.35 } },
        activeProof.query,
      ),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 7 } },
        orderedModels.map((model) => {
          const summary = getSummary(activeProof, model.key);
          const isCandidate = model.key === "candidate";
          return h(
            "div",
            {
              key: model.key,
              style: {
                border: `1px solid ${isCandidate ? "#315d4a" : colors.borderSoft}`,
                background: isCandidate ? "rgba(22, 101, 52, 0.12)" : colors.cardBg,
                borderRadius: 6,
                padding: 8,
              },
            },
            h(
              "div",
              { style: { color: colors.mutedText, fontSize: 10, marginBottom: 2 } },
              model.displayName,
            ),
            h(
              "div",
              { style: { color: colors.strongText, fontSize: 24, fontWeight: 800, lineHeight: 1 } },
              rankLabel(summary),
            ),
            h(
              "div",
              { style: { color: isCandidate ? colors.success : colors.mutedText, fontSize: 10, marginTop: 4 } },
              "target rank",
            ),
          );
        }),
      ),
    ),
    h(SectionTitle, { step: "3", title: "Inspect returned products" }),
    ...orderedModels.map((model) =>
      h(ResultStrip, {
        key: model.key,
        item: activeProof,
        model,
        samplesById,
        loadingSamples,
        onInspectResults,
        onInspectTarget,
        onSelectResult,
      }),
    ),
  );
}

function NeighborhoodChecks({ examples, models, loadingKey, onSelectQuery }) {
  if (!examples.length) {
    return h(
      "div",
      { style: { color: colors.bodyText, fontSize: 12 } },
      "No clickable image-neighborhood examples are configured.",
    );
  }

  return h(
    "div",
    { style: { display: "flex", flexDirection: "column", gap: 10 } },
    h(SectionTitle, { step: "1", title: "Pick an image query" }),
    examples.map((item) =>
      h(
        "div",
        {
          key: item.id,
          style: {
            border: `1px solid ${colors.borderSoft}`,
            borderRadius: 7,
            background: colors.cardBg,
            padding: 9,
            display: "flex",
            flexDirection: "column",
            gap: 8,
          },
        },
        h(
          "div",
          { style: { display: "flex", justifyContent: "space-between", gap: 8 } },
          h("div", { style: { color: colors.strongText, fontSize: 12, fontWeight: 800 } }, item.title),
          h("div", { style: { color: colors.mutedText, fontSize: 10 } }, titleLabel(item.queryLabel)),
        ),
        item.guide
          ? h("div", { style: { color: colors.bodyText, fontSize: 11, lineHeight: 1.35 } }, item.guide)
          : null,
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 6 } },
          models.map((model) => {
            const summary = getSummary(item, model.key);
            const choiceKey = `${item.queryId}:${model.key}`;
            return h(
              MiniButton,
              {
                key: model.key,
                onClick: () => onSelectQuery(item, model),
                title: `Select this product and show ${model.displayName} neighbors`,
              },
              loadingKey === choiceKey
                ? "Loading..."
                : `${model.displayName}: ${summary.hits ?? "-"} / 10`,
            );
          }),
        ),
      ),
    ),
  );
}

export default function CatalogComparisonPanel() {
  const client = usePanelClient();
  const selection = usePanelSelection();
  const samplesState = usePanelSamples();
  const commands = usePanelCommands();
  const panelProps = usePanelProps() || {};
  const [panelError, setPanelError] = React.useState(null);
  const [mode, setMode] = React.useState("text");
  const [activeProofId, setActiveProofId] = React.useState(null);
  const [samplesById, setSamplesById] = React.useState({});
  const [loadingSamples, setLoadingSamples] = React.useState(false);
  const [loadingKey, setLoadingKey] = React.useState(null);

  const models = React.useMemo(() => normalizeModels(panelProps.models), [panelProps.models]);
  const examples = Array.isArray(panelProps.examples) ? panelProps.examples : [];
  const textProofs = examples.filter((item) => item.mode === "text-to-product");
  const neighborhoodExamples = examples.filter((item) => item.queryId);
  const activeProof = textProofs.find((item) => item.id === activeProofId) || textProofs[0] || null;

  React.useEffect(() => {
    if (!activeProofId && textProofs[0]) setActiveProofId(textProofs[0].id);
  }, [activeProofId, textProofs]);

  React.useEffect(() => {
    let cancelled = false;
    const ids = proofSampleIds(activeProof);
    if (!activeProof || !ids.length) {
      setSamplesById({});
      return;
    }

    setLoadingSamples(true);
    client
      .getSamplesByIds(ids, { includeThumbnails: true })
      .then((response) => {
        if (cancelled) return;
        const next = {};
        for (const sample of response.samples || []) next[sample.id] = sample;
        setSamplesById(next);
      })
      .catch((error) => {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : String(error);
        setPanelError(`Could not load returned products: ${message}`);
      })
      .finally(() => {
        if (!cancelled) setLoadingSamples(false);
      });

    return () => {
      cancelled = true;
    };
  }, [client, activeProof?.id]);

  const clearSelection = async () => {
    if (commands.setLabelFilter) commands.setLabelFilter(null);
    setPanelError(null);
    await commands.clearSelection({ persist: false });
  };

  const inspectResultSet = async (item, model) => {
    const ids = resultRows(item, model.key).map((row) => row.id).filter(Boolean);
    if (!ids.length) return;
    const key = `${item.id}:${model.key}:results`;
    setLoadingKey(key);
    setPanelError(null);
    try {
      await commands.clearSelection({ persist: false });
      await commands.setActiveLayout(model.layoutKey, { persist: false });
      await commands.setSelection(ids, { source: "scatter", persist: false });
      commands.focusBuiltin("samples");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setPanelError(`Could not select returned products: ${message}`);
    } finally {
      setLoadingKey(null);
    }
  };

  const inspectTarget = async (item, model) => {
    if (!item.targetSampleId) return;
    const key = `${item.id}:${model.key}:target`;
    setLoadingKey(key);
    setPanelError(null);
    try {
      await commands.clearSelection({ persist: false });
      await commands.setActiveLayout(model.layoutKey, { persist: false });
      await commands.setSelection([item.targetSampleId], { source: "scatter", persist: false });
      commands.focusBuiltin("samples");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setPanelError(`Could not select target product: ${message}`);
    } finally {
      setLoadingKey(null);
    }
  };

  const pickTextProof = (item) => {
    setActiveProofId(item.id);
    const targetModel = models.find((model) => model.key === "candidate") || models[0];
    if (targetModel) {
      inspectTarget(item, targetModel);
    }
  };

  const selectResult = async (model, row) => {
    if (!row?.id) return;
    setPanelError(null);
    try {
      await commands.setActiveLayout(model.layoutKey, { persist: false });
      await commands.setSelection([row.id], { source: "scatter", persist: false });
      commands.focusBuiltin("samples");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setPanelError(`Could not select returned product: ${message}`);
    }
  };

  const selectModelQuery = async (item, model) => {
    const key = `${item.queryId}:${model.key}`;
    setPanelError(null);

    if (!item.queryId) {
      setPanelError("This example is a text-query proof and cannot be selected as an image query.");
      return;
    }

    setLoadingKey(key);
    try {
      await commands.setActiveLayout(model.layoutKey, { persist: false });
      await commands.showSimilar({
        sampleId: item.queryId,
        layoutKey: model.layoutKey,
        k: 10,
        source: `abo-demo:${model.key}`,
        focus: "samples",
        persist: false,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setPanelError(`Could not select image query: ${message}`);
    } finally {
      setLoadingKey(null);
    }
  };

  return h(
    Panel,
    { className: "h-full" },
    h(PanelToolbar, {
      items: [
        { id: "dataset", label: "Data", value: "ABO" },
        { id: "samples", label: "Items", value: String(samplesState.totalSamples ?? "-") },
        { id: "selected", label: "Selected", value: String(selection.selectedIds?.length ?? 0) },
      ],
      actions: h(PanelToolbarButton, { onClick: clearSelection }, "Reset"),
    }),
    h(
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
      h(
        "div",
        {
          style: {
            border: `1px solid ${colors.borderSoft}`,
            background: colors.cardSoft,
            borderRadius: 7,
            padding: 9,
            display: "flex",
            flexDirection: "column",
            gap: 8,
          },
        },
        h(
          "div",
          { style: { color: colors.strongText, fontSize: 13, fontWeight: 850 } },
          "ABO retrieval walkthrough",
        ),
        h(
          "div",
          { style: { color: colors.bodyText, fontSize: 11, lineHeight: 1.35 } },
          "Use text-query proofs for exact variant rank, then image-neighborhood checks for live sample-anchored retrieval.",
        ),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 6 } },
          h(MiniButton, { active: mode === "text", onClick: () => setMode("text") }, "Text queries"),
          h(MiniButton, { active: mode === "image", onClick: () => setMode("image") }, "Image checks"),
        ),
      ),
      mode === "text"
        ? h(TextQueryFlow, {
            proofs: textProofs,
            models,
            activeProof,
            onPickProof: pickTextProof,
            samplesById,
            loadingSamples,
            onInspectResults: inspectResultSet,
            onInspectTarget: inspectTarget,
            onSelectResult: selectResult,
          })
        : h(NeighborhoodChecks, {
            examples: neighborhoodExamples,
            models,
            loadingKey,
            onSelectQuery: selectModelQuery,
          }),
      h(
        "div",
        {
          style: {
            color: colors.mutedText,
            fontSize: 10,
            lineHeight: 1.35,
            borderTop: `1px solid ${colors.borderSoft}`,
            paddingTop: 8,
          },
        },
        "Text-query ranks are from the fixed ABO probe. Clicking a result selects that product in Samples.",
      ),
      panelError
        ? h(
            "div",
            { style: { color: colors.error, fontSize: 11, lineHeight: 1.35 } },
            panelError,
          )
        : null,
    ),
  );
}
