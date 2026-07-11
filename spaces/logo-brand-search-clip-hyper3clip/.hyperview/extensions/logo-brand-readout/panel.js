import { logoCases, logoMetrics } from "./case_data.js";

const sdk = globalThis.HyperViewPanelSDK;
if (!sdk) throw new Error("HyperViewPanelSDK is not available on window.");

const { React, components, hooks } = sdk;
const { Panel, PanelToolbar, PanelToolbarButton } = components;
const { usePanelCommands, usePanelProps, usePanelSelection } = hooks;
const h = React.createElement;

const colors = {
  surface: "#0f141d",
  surface2: "#151b26",
  surface3: "#1a2230",
  border: "rgba(148, 163, 184, 0.22)",
  borderSoft: "rgba(148, 163, 184, 0.14)",
  text: "#e5eefb",
  strong: "#f8fafc",
  muted: "#94a3b8",
  body: "#cbd5e1",
  hyper: "#93c5fd",
  hyperSoft: "rgba(147, 197, 253, 0.12)",
  clip: "#94a3b8",
  clipSoft: "rgba(100, 116, 139, 0.13)",
  proof: "#f8fafc",
  proofSoft: "rgba(248, 250, 252, 0.10)",
  danger: "#f87171",
};

const models = {
  hyper3: {
    key: "hyper3",
    title: "Hyper3-CLIP",
    resultKey: "hyper3Results",
    metricKey: "hyper3_clip",
    accent: colors.hyper,
    soft: colors.hyperSoft,
    summary: "Exact visual brief lands at the top.",
  },
  clip: {
    key: "clip",
    title: "CLIP B/32",
    resultKey: "clipResults",
    metricKey: "clip_b32",
    accent: colors.clip,
    soft: colors.clipSoft,
    summary: "Nearby category matches outrank the target.",
  },
};

function textStyle(size = 12, color = colors.body, weight = 500, lineHeight = 1.35) {
  return { color, fontSize: size, fontWeight: weight, lineHeight, letterSpacing: 0 };
}

function rankCopy(rank) {
  return rank || rank === 0 ? `#${rank}` : "-";
}

function cleanQuery(text) {
  return String(text || "").replace(/^"+|"+$/g, "");
}

function selectedIds(selection) {
  if (Array.isArray(selection?.selectedIds)) return selection.selectedIds;
  if (Array.isArray(selection?.sampleIds)) return selection.sampleIds;
  if (Array.isArray(selection)) return selection;
  return [];
}

function allSampleIdsForCase(item) {
  if (!item) return [];
  return [
    item.target?.sampleId,
    item.clipTargetProof?.sampleId,
    ...(item.hyper3Results || []).map((result) => result.sampleId),
    ...(item.clipResults || []).map((result) => result.sampleId),
  ].filter(Boolean);
}

function findCaseFromSelection(cases, selection, activeCaseId) {
  const ids = new Set(selectedIds(selection));
  if (!ids.size) return null;
  const active = cases.find((item) => item.id === activeCaseId);
  if (active && allSampleIdsForCase(active).some((id) => ids.has(id))) return active;
  return cases.find((item) => allSampleIdsForCase(item).some((id) => ids.has(id))) || null;
}

function Card({ children, style }) {
  return h(
    "div",
    {
      style: {
        border: `1px solid ${colors.borderSoft}`,
        background: colors.surface,
        borderRadius: 6,
        ...style,
      },
    },
    children,
  );
}

function Pill({ children, color = colors.muted, bg = "rgba(148, 163, 184, 0.10)" }) {
  return h(
    "span",
    {
      style: {
        display: "inline-flex",
        alignItems: "center",
        border: `1px solid ${color}`,
        borderRadius: 999,
        color,
        background: bg,
        padding: "3px 7px",
        fontSize: 10,
        fontWeight: 800,
        whiteSpace: "nowrap",
      },
    },
    children,
  );
}

function CasePicker({ cases, selectedId, onSelect }) {
  return h(
    "div",
    {
      style: {
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(132px, 1fr))",
        gap: 7,
      },
    },
    cases.map((item, index) => {
      const active = item.id === selectedId;
      return h(
        "button",
        {
          key: item.id,
          type: "button",
          onClick: () => onSelect(item),
          style: {
            minHeight: 54,
            border: `1px solid ${active ? colors.hyper : colors.border}`,
            borderRadius: 6,
            background: active ? colors.hyperSoft : colors.surface,
            color: colors.text,
            cursor: "pointer",
            padding: "8px 9px",
            textAlign: "left",
          },
        },
        h("div", { style: textStyle(10, active ? colors.hyper : colors.muted, 850, 1.2) }, `Case ${index + 1}`),
        h("div", { style: textStyle(12, colors.strong, 850, 1.2) }, item.label),
        h(
          "div",
          { style: { ...textStyle(10, colors.body, 700, 1.2), marginTop: 3 } },
          `${rankCopy(item.targetRanks.hyper3_clip)} vs ${rankCopy(item.targetRanks.clip_b32)}`,
        ),
      );
    }),
  );
}

function Metric({ label, value, note, accent = colors.strong }) {
  return h(
    Card,
    { style: { padding: 10, background: colors.surface2 } },
    h("div", { style: textStyle(10, colors.muted, 750, 1.2) }, label),
    h("div", { style: { ...textStyle(22, accent, 900, 1.05), marginTop: 4 } }, value),
    note ? h("div", { style: { ...textStyle(10, colors.body, 650, 1.2), marginTop: 4 } }, note) : null,
  );
}

function MetricRow({ item }) {
  return h(
    "div",
    {
      style: {
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
        gap: 8,
      },
    },
    h(Metric, {
      label: "This brief",
      value: `${rankCopy(item.targetRanks.hyper3_clip)} vs ${rankCopy(item.targetRanks.clip_b32)}`,
      note: "target rank",
      accent: colors.proof,
    }),
    h(Metric, {
      label: "Hit@1",
      value: logoMetrics.text_to_logo.hyper3_hit1,
      note: `CLIP ${logoMetrics.text_to_logo.clip_hit1}`,
      accent: colors.hyper,
    }),
    h(Metric, {
      label: "Hit@5",
      value: logoMetrics.text_to_logo.hyper3_hit5,
      note: `CLIP ${logoMetrics.text_to_logo.clip_hit5}`,
      accent: colors.hyper,
    }),
  );
}

function BriefCard({ item, onSelect }) {
  return h(
    Card,
    {
      style: {
        padding: 10,
        display: "grid",
        gridTemplateColumns: "96px minmax(0, 1fr)",
        gap: 10,
        alignItems: "stretch",
      },
    },
    h(
      "button",
      {
        type: "button",
        onClick: () => onSelect(item.target.sampleId, "target-logo"),
        style: {
          border: `1px solid ${colors.proof}`,
          background: "#ffffff",
          padding: 6,
          cursor: "pointer",
          borderRadius: 6,
          minWidth: 0,
        },
      },
      h("img", {
        src: item.target.image,
        alt: `${item.label} target logo`,
        style: {
          width: "100%",
          aspectRatio: "1 / 1",
          objectFit: "contain",
          borderRadius: 4,
          display: "block",
          background: "#ffffff",
        },
      }),
    ),
    h(
      "div",
      { style: { display: "flex", flexDirection: "column", minWidth: 0, gap: 7 } },
      h(
        "div",
        { style: { display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" } },
        h("div", { style: textStyle(11, colors.muted, 850, 1.2) }, "Search brief"),
        h(Pill, { color: colors.proof, bg: colors.proofSoft }, `${item.sampleCount} logos`),
      ),
      h(
        "div",
        {
          style: {
            ...textStyle(13, colors.strong, 760, 1.28),
            display: "-webkit-box",
            overflow: "hidden",
            WebkitLineClamp: 3,
            WebkitBoxOrient: "vertical",
          },
        },
        cleanQuery(item.query),
      ),
      h("div", { style: textStyle(11, colors.body, 650, 1.25) }, item.business),
    ),
  );
}

function ResultCard({ result, model, onSelect, loading }) {
  const target = Boolean(result.isTarget);
  const key = `${model.key}:${result.sampleId}`;
  return h(
    "button",
    {
      key,
      type: "button",
      onClick: () => onSelect(result.sampleId, `${model.key}-rank-${result.rank}`),
      disabled: loading === key,
      title: `${model.title} rank ${result.rank}`,
      style: {
        border: `1px solid ${target ? colors.proof : colors.borderSoft}`,
          background: target ? colors.hyperSoft : "#0b111a",
        borderRadius: 6,
        padding: 6,
        color: colors.text,
        cursor: loading === key ? "default" : "pointer",
        opacity: loading === key ? 0.7 : 1,
        textAlign: "left",
        minWidth: 0,
      },
    },
    h(
      "div",
      {
        style: {
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 5,
          marginBottom: 5,
        },
      },
      h("span", { style: textStyle(11, colors.strong, 900, 1) }, rankCopy(result.rank)),
      target ? h(Pill, { color: colors.proof, bg: "transparent" }, "target") : null,
    ),
    h("img", {
      src: result.image,
      alt: `${model.title} rank ${result.rank}`,
      style: {
        width: "100%",
        aspectRatio: "1 / 1",
        objectFit: "contain",
        borderRadius: 5,
        display: "block",
        background: "#ffffff",
      },
    }),
    h(
      "div",
      {
        style: {
          ...textStyle(10, colors.body, 650, 1.2),
          marginTop: 5,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        },
      },
      cleanQuery(result.text),
    ),
  );
}

function ResultColumn({ item, model, onSelect, loading }) {
  const results = item[model.resultKey] || [];
  const targetRank = item.targetRanks?.[model.metricKey];
  const offscreenProof = model.key === "clip" && item.clipTargetProof;
  return h(
    Card,
    { style: { padding: 10, background: model.key === "hyper3" ? colors.hyperSoft : colors.clipSoft } },
    h(
      "div",
      {
        style: {
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 10,
          marginBottom: 8,
        },
      },
      h(
        "div",
        null,
        h("div", { style: textStyle(13, model.accent, 900, 1.15) }, model.title),
        h("div", { style: textStyle(10, colors.body, 650, 1.2) }, model.summary),
      ),
      h("div", { style: textStyle(25, model.accent, 900, 1) }, rankCopy(targetRank)),
    ),
    h(
      "div",
      {
        style: {
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(78px, 1fr))",
          gap: 6,
        },
      },
      results.map((result) => h(ResultCard, { key: result.sampleId, result, model, onSelect, loading })),
    ),
    offscreenProof
      ? h(
          "button",
          {
            type: "button",
            onClick: () => onSelect(item.clipTargetProof.sampleId, "clip-target-proof"),
            style: {
              marginTop: 8,
              width: "100%",
              border: `1px solid ${colors.danger}`,
              borderRadius: 6,
              padding: "7px 9px",
              background: "rgba(248, 113, 113, 0.10)",
              color: colors.text,
              cursor: "pointer",
              textAlign: "left",
            },
          },
          h("span", { style: textStyle(11, colors.danger, 850) }, `Target appears at ${rankCopy(item.clipTargetProof.rank)} for CLIP`),
        )
      : null,
  );
}

function ComparisonGrid({ item, onSelect, loading }) {
  return h(
    "div",
    {
      style: {
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
        gap: 10,
      },
    },
    h(ResultColumn, { item, model: models.hyper3, onSelect, loading }),
    h(ResultColumn, { item, model: models.clip, onSelect, loading }),
  );
}

export default function LogoBrandComparisonPanel() {
  const panelProps = usePanelProps();
  const commands = usePanelCommands();
  const selection = usePanelSelection();
  const [activeCaseId, setActiveCaseId] = React.useState(
    typeof panelProps.initialCaseId === "string" ? panelProps.initialCaseId : logoCases[0]?.id,
  );
  const [loading, setLoading] = React.useState(null);
  const [panelError, setPanelError] = React.useState(null);

  const selectedCase = findCaseFromSelection(logoCases, selection, activeCaseId);
  const activeCase = selectedCase || logoCases.find((item) => item.id === activeCaseId) || logoCases[0];

  React.useEffect(() => {
    if (selectedCase?.id && selectedCase.id !== activeCaseId) {
      setActiveCaseId(selectedCase.id);
    }
  }, [selectedCase, activeCaseId]);

  const selectSample = React.useCallback(
    async (sampleId, source) => {
      if (!sampleId) return;
      const loadingKey = source.startsWith("hyper3") ? `hyper3:${sampleId}` : source.startsWith("clip") ? `clip:${sampleId}` : source;
      setPanelError(null);
      setLoading(loadingKey);
      try {
        await commands.setSelection([sampleId], { persist: false, source: `logo-brand:${source}` });
        commands.focusPanel("grid");
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        setPanelError(`Could not select sample: ${message}`);
      } finally {
        setLoading(null);
      }
    },
    [commands],
  );

  const selectCase = React.useCallback(
    async (item) => {
      setActiveCaseId(item.id);
      setPanelError(null);
      try {
        await commands.setSelection([], { persist: false, source: "logo-brand:case" });
        commands.focusPanel("logo-brand-results");
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        setPanelError(`Could not reset sample grid: ${message}`);
      }
    },
    [commands],
  );

  if (!activeCase) {
    return h(Panel, null, h("div", { style: { padding: 16, color: colors.text } }, "No logo cases are available."));
  }

  return h(
    Panel,
    null,
    h(
      PanelToolbar,
      { title: "Logo Search" },
      h(PanelToolbarButton, { onClick: () => commands.focusPanel("grid") }, "Samples"),
    ),
    h(
      "div",
      {
        style: {
          flex: "1 1 auto",
          minHeight: 0,
          overflowY: "auto",
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          minWidth: 0,
          boxSizing: "border-box",
        },
      },
      h(
        "div",
        {
          style: {
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: 12,
          },
        },
        h(
          "div",
          { style: { minWidth: 0 } },
          h("div", { style: textStyle(10, colors.hyper, 900, 1.15) }, "Hyper3-CLIP vs CLIP B/32"),
          h("div", { style: textStyle(23, colors.strong, 900, 1.08) }, "Brand Asset Search"),
          h(
            "div",
            { style: { ...textStyle(12, colors.body, 650, 1.3), marginTop: 4, maxWidth: 620 } },
            "Retrieval for logo libraries where the brief names objects, layout, palette, and style.",
          ),
        ),
        h(Pill, { color: colors.proof, bg: colors.proofSoft }, `MRR ${logoMetrics.text_to_logo.mrr_delta}`),
      ),
      h(CasePicker, {
        cases: logoCases,
        selectedId: activeCase.id,
        onSelect: selectCase,
      }),
      h(BriefCard, { item: activeCase, onSelect: selectSample }),
      h(MetricRow, { item: activeCase }),
      h(ComparisonGrid, { item: activeCase, onSelect: selectSample, loading }),
      panelError
        ? h(
            "div",
            {
              style: {
                border: `1px solid ${colors.danger}`,
                color: colors.danger,
                borderRadius: 6,
                padding: 8,
                fontSize: 12,
              },
            },
            panelError,
          )
        : null,
    ),
  );
}
