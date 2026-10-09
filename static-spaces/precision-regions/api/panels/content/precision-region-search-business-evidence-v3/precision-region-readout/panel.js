const sdk = globalThis.HyperViewPanelSDK;
if (!sdk || sdk.version !== "2") {
  throw new Error("HyperViewPanelSDK v2 is not available on window.");
}
const { React, components = {}, hooks } = sdk;
const Panel = components.Panel || (({ children, className = "" }) => /* @__PURE__ */ React.createElement("div", { className: `flex flex-col h-full bg-card overflow-hidden ${className}`.trim(), style: { height: "100%" } }, children));
const { usePanelActions, usePanelState, useSample, useSampleResults, useSelection } = hooks;
function mediaUrl(sample) {
  const raw = sample?.media_url || sample?.thumbnail_url || sample?.thumbnail;
  return typeof raw === "string" && raw ? raw : null;
}
function formatBox(bbox) {
  if (!Array.isArray(bbox) || bbox.length !== 4)
    return "unknown";
  const [x, y, w, h] = bbox.map((value) => Number(value).toFixed(1));
  return `${x}, y ${y}, ${w}\xD7${h}`;
}
function formatSize(size) {
  if (!Array.isArray(size) || size.length !== 2)
    return "size unknown";
  return `${size[0]}\xD7${size[1]}`;
}
function RankCard({ name, color, rank }) {
  const consequence = rank === 1 ? "Found first" : rank <= 5 ? `Visible at #${rank}` : `${rank - 1} regions appear first`;
  return /* @__PURE__ */ React.createElement("article", { className: "pr-rank-card" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("i", { style: { background: color } }), name), /* @__PURE__ */ React.createElement("strong", { style: { color } }, "#", rank), /* @__PURE__ */ React.createElement("small", null, consequence));
}
export default function PrecisionRegionPanel() {
  const { props = {}, state = {}, patchState } = usePanelState();
  const { updateProps } = usePanelActions();
  const { showResults } = useSampleResults();
  const { setSelection } = useSelection();
  const cases = Array.isArray(props.cases) ? props.cases : [];
  const active = cases.find((item) => item.id === state.activeCaseId) || cases[0] || null;
  const { sample: source, error: sourceError } = useSample(active?.sourceSampleId);
  const { sample: target, error: targetError } = useSample(active?.targetSampleId);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);
  const clipPanelId = typeof props.clipPanelId === "string" && props.clipPanelId ? props.clipPanelId : "precision-clip-results";
  const chooseCase = (item) => {
    if (busy)
      return;
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        await showResults(
          item.results.hyper3.map((result) => result.sampleId),
          { focus: false, source: `${item.shortLabel} \xB7 Hyper3-CLIP \xB7 Top 5` }
        );
        await updateProps(clipPanelId, { mode: "results", collectionId: item.collectionIds.clip });
        await patchState({ activeCaseId: item.id });
        await setSelection([item.targetSampleId]);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : String(reason));
      } finally {
        setBusy(false);
      }
    })();
  };
  if (!active)
    return /* @__PURE__ */ React.createElement(Panel, null, /* @__PURE__ */ React.createElement("div", { className: "pr-root" }, "No Precision Regions cases are available."));
  const sourceUrl = mediaUrl(source);
  const targetUrl = mediaUrl(target);
  const benchmark = props.benchmark || {};
  return /* @__PURE__ */ React.createElement(Panel, null, /* @__PURE__ */ React.createElement("div", { className: "pr-root" }, /* @__PURE__ */ React.createElement("style", null, `
          .pr-root,.pr-root *{box-sizing:border-box}.pr-root{flex:1;min-height:0;overflow:auto;padding:14px;color:var(--hv-color-foreground);background:var(--hv-color-background);font:11px/1.42 system-ui,-apple-system,BlinkMacSystemFont,sans-serif}.pr-kicker{display:block;color:var(--hv-color-muted-foreground);font-size:9px;font-weight:800;letter-spacing:.09em;text-transform:uppercase}.pr-header h2{margin:3px 0 0;font-size:18px;line-height:1.15;letter-spacing:-.02em}.pr-header p{margin:6px 0 0;color:var(--hv-color-muted-foreground)}.pr-query{margin:12px 0 0;padding:9px 10px;border-left:2px solid var(--hv-color-accent);background:var(--hv-color-surface-muted);font-size:13px;font-weight:680}.pr-visual{position:relative;margin-top:10px;min-height:176px;overflow:hidden;border:1px solid var(--hv-color-border);border-radius:9px;background:var(--hv-color-surface-muted);cursor:pointer}.pr-visual>img{display:block;width:100%;height:210px;object-fit:cover}.pr-crop{position:absolute;right:8px;bottom:8px;width:86px;height:86px;padding:4px;border:1px solid rgba(255,255,255,.8);border-radius:7px;background:rgba(8,12,18,.9);box-shadow:0 5px 20px rgba(0,0,0,.35)}.pr-crop img{width:100%;height:100%;object-fit:contain}.pr-crop span,.pr-visual-label{position:absolute;border-radius:4px;padding:3px 6px;background:rgba(8,12,18,.82);color:white;font-size:8px;font-weight:800;text-transform:uppercase;letter-spacing:.06em}.pr-visual-label{left:8px;top:8px}.pr-crop span{right:3px;bottom:3px}.pr-ranks{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px}.pr-rank-card{border:1px solid var(--hv-color-border);border-radius:8px;padding:9px;background:var(--hv-color-surface)}.pr-rank-card div{display:flex;align-items:center;gap:5px;font-weight:720}.pr-rank-card i{width:7px;height:7px;border-radius:99px}.pr-rank-card strong{display:block;margin-top:2px;font-size:18px}.pr-rank-card small{display:block;color:var(--hv-color-muted-foreground);font-size:9px}.pr-cases{display:grid;grid-template-columns:repeat(2,1fr);gap:5px;margin-top:10px}.pr-case{min-width:0;border:1px solid var(--hv-color-border);border-radius:7px;padding:7px 6px;background:var(--hv-color-surface);color:var(--hv-color-foreground);text-align:left;cursor:pointer}.pr-case[aria-pressed=true]{border-color:var(--hv-color-accent);box-shadow:inset 0 0 0 1px var(--hv-color-accent)}.pr-case strong,.pr-case small{display:block;overflow:hidden;text-overflow:ellipsis}.pr-case strong{font-size:9px}.pr-case small{margin-top:2px;color:var(--hv-color-muted-foreground);font-size:8px}.pr-benchmark{margin-top:13px;border-top:1px solid var(--hv-color-border);padding-top:10px}.pr-benchmark h3{margin:3px 0 2px;font-size:12px}.pr-caption{margin:0 0 7px;color:var(--hv-color-muted-foreground);font-size:9px}.pr-table{width:100%;border-collapse:collapse;font-size:9px}.pr-table th,.pr-table td{padding:5px 4px;border-bottom:1px solid var(--hv-color-border);text-align:right}.pr-table th:first-child,.pr-table td:first-child{text-align:left}.pr-table th{color:var(--hv-color-muted-foreground);font-size:8px;text-transform:uppercase}.pr-note{margin:7px 0 0;color:var(--hv-color-muted-foreground);font-size:9px}.pr-error{color:#ef4444}.pr-busy{opacity:.62}@media(max-width:390px){.pr-root{padding:10px}.pr-ranks{grid-template-columns:1fr}.pr-visual>img{height:180px}}
        `), /* @__PURE__ */ React.createElement("header", { className: "pr-header" }, /* @__PURE__ */ React.createElement("span", { className: "pr-kicker" }, "Language-guided region search"), /* @__PURE__ */ React.createElement("h2", null, "Which region matches the description?"), /* @__PURE__ */ React.createElement("p", null, "Each case boxes the annotated RefCOCOg region in its own source photo. The two lists are each model\u2019s top five from the shared crop pool; the cards below give the rank the boxed region actually reached.")), /* @__PURE__ */ React.createElement("blockquote", { className: "pr-query" }, "\u201C", active.query, "\u201D"), /* @__PURE__ */ React.createElement("button", { type: "button", className: "pr-visual", onClick: () => void setSelection([active.targetSampleId]) }, sourceUrl ? /* @__PURE__ */ React.createElement("img", { src: sourceUrl, alt: `${active.shortLabel} source scene` }) : null, /* @__PURE__ */ React.createElement("span", { className: "pr-visual-label" }, "Annotated region in the source photo"), /* @__PURE__ */ React.createElement("span", { className: "pr-crop" }, targetUrl ? /* @__PURE__ */ React.createElement("img", { src: targetUrl, alt: active.query || "Target crop" }) : null, /* @__PURE__ */ React.createElement("span", null, "Target"))), /* @__PURE__ */ React.createElement("p", { className: "pr-note" }, "Source image ", active.sourceImageId, " \xB7 ", formatSize(active.imageSize), " \xB7 box x ", formatBox(active.bbox), " \xB7 RefCOCOg query ", active.questionId, ". Every tile in this Space carries its own image id, box and query id in its metadata, so any crop here can be re-cut from RefCOCOg."), /* @__PURE__ */ React.createElement("section", { className: "pr-ranks", "aria-label": "Exact target ranks" }, /* @__PURE__ */ React.createElement(RankCard, { name: "Hyper3-CLIP", color: "#60a5fa", rank: active.target.hyper3Rank }), /* @__PURE__ */ React.createElement(RankCard, { name: "OpenAI CLIP", color: "#f59e0b", rank: active.target.clipRank })), /* @__PURE__ */ React.createElement("p", { className: "pr-note" }, "Both models rank the same pool of ", benchmark.queryCount || 180, " region crops cut from across the source images; each list shows its top five, so a boxed region ranked below five is not in the visible shortlist."), /* @__PURE__ */ React.createElement("nav", { className: "pr-cases", "aria-label": "Object search examples" }, cases.map((item) => /* @__PURE__ */ React.createElement("button", { key: item.id, type: "button", className: `pr-case${busy ? " pr-busy" : ""}`, "aria-pressed": item.id === active.id, disabled: busy, onClick: () => chooseCase(item) }, /* @__PURE__ */ React.createElement("strong", null, item.shortLabel), /* @__PURE__ */ React.createElement("small", null, item.context)))), /* @__PURE__ */ React.createElement("section", { className: "pr-benchmark", "aria-label": "Full benchmark results" }, /* @__PURE__ */ React.createElement("span", { className: "pr-kicker" }, "How the models compare"), /* @__PURE__ */ React.createElement("h3", null, "RefCOCOg \xB7 ", benchmark.queryCount || 180, " descriptions"), /* @__PURE__ */ React.createElement("p", { className: "pr-caption" }, "One correct region per description in this 180-description diagnostic subset."), /* @__PURE__ */ React.createElement("table", { className: "pr-table" }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "Correct region"), /* @__PURE__ */ React.createElement("th", { style: { color: "#60a5fa" } }, "Hyper3"), /* @__PURE__ */ React.createElement("th", { style: { color: "#f59e0b" } }, "CLIP"))), /* @__PURE__ */ React.createElement("tbody", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("td", null, "Ranked first"), /* @__PURE__ */ React.createElement("td", null, benchmark.hyper3Hit1), /* @__PURE__ */ React.createElement("td", null, benchmark.clipHit1)), /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("td", null, "Within top ten"), /* @__PURE__ */ React.createElement("td", null, benchmark.hyper3Hit10), /* @__PURE__ */ React.createElement("td", null, benchmark.clipHit10)), /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("td", null, "Average rank score"), /* @__PURE__ */ React.createElement("td", null, benchmark.hyper3Mrr), /* @__PURE__ */ React.createElement("td", null, benchmark.clipMrr)))), /* @__PURE__ */ React.createElement("p", { className: "pr-note" }, "The four cases are diagnostic, not a highlight reel: two show Hyper3-CLIP surfacing a region the baseline buries, one is a narrow win, and one is a case the baseline wins outright. The table covers the whole subset and is descriptive, not a significance claim.")), sourceError || targetError ? /* @__PURE__ */ React.createElement("div", { className: "pr-error" }, sourceError || targetError) : null, error ? /* @__PURE__ */ React.createElement("div", { className: "pr-error", role: "alert" }, error) : null));
}
