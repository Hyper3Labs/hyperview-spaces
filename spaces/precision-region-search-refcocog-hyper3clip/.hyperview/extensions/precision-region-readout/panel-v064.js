import { rankedCases } from "./case_data.js";

const sdk = globalThis.HyperViewPanelSDK;
if (!sdk) throw new Error("HyperViewPanelSDK is not available on window.");

const { React, components, hooks } = sdk;
const { Panel, PanelToolbar, PanelToolbarButton } = components;
const { usePanelCommands, usePanelProps, usePanelSelection } = hooks;
const h = React.createElement;

const colors = {
  panelBg: "#0b1120",
  surface: "#111827",
  surface2: "#172033",
  border: "#2b3a52",
  text: "#e5e7eb",
  strong: "#f8fafc",
  muted: "#94a3b8",
  body: "#cbd5e1",
  hyper: "#7dd3fc",
  clip: "#c4b5fd",
  success: "#86efac",
  error: "#fca5a5",
};

function textStyle(size = 12, color = colors.body, weight = 500, lineHeight = 1.35) {
  return { color, fontSize: size, fontWeight: weight, lineHeight, letterSpacing: 0 };
}

function selectedIds(selection) {
  if (Array.isArray(selection?.selectedIds)) return selection.selectedIds;
  if (Array.isArray(selection?.sampleIds)) return selection.sampleIds;
  if (Array.isArray(selection)) return selection;
  return [];
}

function modelByKey(models, key) {
  return models.find((model) => model.key === key) || null;
}

function Card({ children, style }) {
  return h(
    "div",
    {
      style: {
        border: `1px solid ${colors.border}`,
        background: colors.surface,
        borderRadius: 6,
        ...style,
      },
    },
    children,
  );
}

function StepLabel({ number, label }) {
  return h(
    "div",
    { style: { display: "flex", alignItems: "center", gap: 7 } },
    h(
      "span",
      {
        style: {
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 19,
          height: 19,
          borderRadius: 5,
          background: colors.surface2,
          color: colors.hyper,
          fontSize: 11,
          fontWeight: 900,
        },
      },
      number,
    ),
    h("span", { style: textStyle(11, colors.strong, 900) }, label),
  );
}

function SliceButton({ item, active, onClick, disabled }) {
  return h(
    "button",
    {
      type: "button",
      onClick,
      disabled,
      style: {
        width: "100%",
        border: `1px solid ${active ? colors.hyper : colors.border}`,
        background: active ? "rgba(125, 211, 252, 0.11)" : colors.surface,
        color: disabled ? colors.muted : colors.text,
        borderRadius: 6,
        padding: "7px 8px",
        cursor: disabled ? "default" : "pointer",
        textAlign: "left",
      },
    },
    h("div", { style: textStyle(11, colors.strong, 850) }, item.label),
    h(
      "div",
      { style: { ...textStyle(9, colors.body, 650), marginTop: 2 } },
      `Target crop: Hyper3 ${item.metric.hyper3_clip} | CLIP ${item.metric.clip_b32}`,
    ),
  );
}

function Metric({ label, value, color, note }) {
  return h(
    "div",
    {
      style: {
        border: `1px solid ${colors.border}`,
        background: "#0f172a",
        borderRadius: 6,
        padding: "7px 8px",
      },
    },
    h("div", { style: textStyle(8, colors.muted, 800) }, label),
    h("div", { style: { ...textStyle(15, color, 900, 1.05), marginTop: 2 } }, value),
    note ? h("div", { style: { ...textStyle(8, colors.body, 650), marginTop: 2 } }, note) : null,
  );
}

function rankedProps(model, item) {
  const source = model.key === "hyper3" ? "Hyper3-CLIP hyperbolic distance" : "CLIP B/32 cosine distance";
  return {
    mode: "ranked",
    rank: {
      anchorSampleId: item.sourceSampleId,
      layoutKey: model.layoutKey,
      k: item.sampleCount,
      source,
    },
  };
}

export default function PrecisionRegionComparisonPanel() {
  const props = usePanelProps();
  const commands = usePanelCommands();
  const selection = usePanelSelection();
  const models = Array.isArray(props.models) ? props.models : [];
  const hyper3 = modelByKey(models, "hyper3");
  const clip = modelByKey(models, "clip");
  const [activeCaseId, setActiveCaseId] = React.useState(
    typeof props.initialCaseId === "string" ? props.initialCaseId : rankedCases[0]?.id,
  );
  const [loadingCaseId, setLoadingCaseId] = React.useState(null);
  const [panelError, setPanelError] = React.useState(null);

  const activeCase = rankedCases.find((item) => item.id === activeCaseId) || rankedCases[0];

  const patchRankPanel = React.useCallback(
    async (model, item) => {
      if (!model?.rankPanelId) {
        throw new Error("No active ranked panel");
      }
      return commands.updatePanelProps(model.rankPanelId, rankedProps(model, item));
    },
    [commands],
  );

  const chooseCase = React.useCallback(
    async (caseId) => {
      const item = rankedCases.find((entry) => entry.id === caseId);
      if (!item || !hyper3 || !clip) return;
      setLoadingCaseId(caseId);
      setPanelError(null);
      try {
        await Promise.all([patchRankPanel(hyper3, item), patchRankPanel(clip, item)]);
        await commands.setActiveLayout(hyper3.layoutKey, { persist: false });
        await commands.setSelection([item.sourceSampleId], {
          persist: false,
          source: `ranked-crops:${caseId}:source`,
        });
        setActiveCaseId(caseId);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        setPanelError(`Could not switch ranked crops: ${message}`);
      } finally {
        setLoadingCaseId(null);
      }
    },
    [commands, hyper3, clip, patchRankPanel],
  );

  const resetCase = React.useCallback(() => {
    if (activeCase) void chooseCase(activeCase.id);
  }, [activeCase, chooseCase]);

  const toolbar = h(PanelToolbar, {
    items: [
      { id: "dataset", label: "Data", value: props.dataset || "RefCOCOg" },
      { id: "crops", label: "Crops", value: String(activeCase?.sampleCount ?? "-") },
      { id: "selected", label: "Selected", value: String(selectedIds(selection).length) },
    ],
    actions: h(PanelToolbarButton, { onClick: resetCase }, "Reset anchor"),
  });

  const content = h(
    "div",
    {
      style: {
        height: "100%",
        overflow: "auto",
        background: colors.panelBg,
        padding: 10,
      },
    },
    h(
      "div",
      { style: { display: "flex", flexDirection: "column", gap: 8 } },
      h(
        "header",
        null,
        h("div", { style: textStyle(10, colors.hyper, 900) }, "REFCOCOG CROP RANKING"),
        h(
          "h2",
          {
            style: {
              color: colors.strong,
              fontSize: 17,
              fontWeight: 900,
              lineHeight: 1.12,
              margin: "4px 0 0",
              letterSpacing: 0,
            },
          },
          "Same image, exact crop",
        ),
        h(
          "p",
          { style: { ...textStyle(10, colors.body, 600, 1.3), margin: "5px 0 0" } },
          "Each ranked Samples panel uses the boxed source scene as its anchor and ranks real crops from that same image.",
        ),
      ),
      h(
        Card,
        { style: { padding: 8 } },
        h(StepLabel, { number: "1", label: "Choose the source scene" }),
        h(
          "div",
          { style: { display: "grid", gap: 5, marginTop: 7 } },
          rankedCases.map((item) =>
            h(SliceButton, {
              key: item.id,
              item,
              active: item.id === activeCase?.id,
              disabled: loadingCaseId !== null,
              onClick: () => chooseCase(item.id),
            }),
          ),
        ),
      ),
      activeCase
        ? h(
            Card,
            { style: { padding: 8 } },
            h(StepLabel, { number: "2", label: "Compare model ranks" }),
            h("div", { style: { ...textStyle(13, colors.strong, 850, 1.25), marginTop: 7 } }, activeCase.query),
            h(
              "div",
              { style: { ...textStyle(9, colors.body, 650, 1.25), marginTop: 4 } },
              activeCase.business,
            ),
            h(
              "div",
              {
                style: {
                  display: "grid",
                  gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                  gap: 5,
                  marginTop: 7,
                },
              },
              h(Metric, {
                label: "Hyper3",
                value: activeCase.metric.hyper3_clip,
                color: colors.hyper,
                note: "target crop",
              }),
              h(Metric, {
                label: "CLIP",
                value: activeCase.metric.clip_b32,
                color: colors.clip,
                note: "target crop",
              }),
              h(Metric, {
                label: "Lift",
                value: activeCase.metric.delta,
                color: colors.success,
                note: `${activeCase.sampleCount} crops`,
              }),
            ),
          )
        : null,
      activeCase
        ? h(
            Card,
            { style: { padding: 8, background: "rgba(125, 211, 252, 0.055)" } },
            h("div", { style: textStyle(11, colors.strong, 900) }, "What to look for"),
            h(
              "div",
              { style: { ...textStyle(10, colors.body, 650, 1.3), marginTop: 4 } },
              `The Hyper3 panel should put \"${activeCase.targetLabel}\" first. The CLIP panel ranks a different crop above it, which is the failure mode this demo is meant to expose.`,
            ),
          )
        : null,
      h(
        "div",
        { style: textStyle(9, colors.muted, 600, 1.3) },
        "This uses HyperView's builtin ranked Samples mode. The rank source is model distance from the selected source-scene anchor.",
      ),
      panelError ? h("div", { style: textStyle(11, colors.error, 700, 1.35) }, panelError) : null,
    ),
  );

  return h(Panel, { className: "h-full" }, toolbar, content);
}
