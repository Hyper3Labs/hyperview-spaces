const sdk = globalThis.HyperViewPanelSDK;
if (!sdk || sdk.version !== "2") throw new Error("HyperViewPanelSDK v2 is required.");

const { React, components = {}, hooks = {} } = sdk;
const Panel = components.Panel || (({ children }) => (
  <div className="flex flex-col h-full bg-card overflow-hidden">{children}</div>
));
const { usePanelActions, usePanelState, useSelection } = hooks;

const css = `
.geo-root,.geo-root *{box-sizing:border-box}
.geo-root{flex:1;min-height:0;overflow:auto;overscroll-behavior:contain;padding:14px 16px;color:var(--hv-color-foreground);background:var(--hv-color-background);font:12px/1.5 system-ui,-apple-system,BlinkMacSystemFont,sans-serif;container-type:inline-size}
.geo-kicker{display:block;color:var(--hv-color-muted-foreground);font-size:10px;font-weight:650;letter-spacing:.07em;text-transform:uppercase}
.geo-header{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.geo-header h2{margin:4px 0 0;font-size:20px;line-height:1.2;letter-spacing:-.025em;font-weight:650}
.geo-intro{margin:8px 0 0;color:var(--hv-color-muted-foreground)}
.geo-scope{margin:8px 0 0;color:var(--hv-color-muted-foreground);font-size:10px}
.geo-reset{flex:none;border:1px solid var(--hv-color-border);border-radius:5px;padding:4px 7px;color:var(--hv-color-muted-foreground);background:transparent;cursor:pointer;font:inherit;font-size:10px}
.geo-reset:disabled,.geo-case:disabled{opacity:.55;cursor:wait}
.geo-section{margin-top:16px}
.geo-cases{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px}
.geo-case{min-width:0;border:1px solid var(--hv-color-border);border-radius:7px;padding:10px 11px;color:var(--hv-color-muted-foreground);background:var(--hv-color-surface);cursor:pointer;text-align:left;font:inherit}
.geo-case[aria-pressed=true]{border-color:#60a5fa;color:var(--hv-color-foreground);background:color-mix(in srgb,#60a5fa 10%,var(--hv-color-surface));box-shadow:inset 3px 0 #60a5fa}
.geo-case:hover{border-color:var(--hv-color-muted-foreground)}
.geo-case strong{display:block;font-size:12px;font-weight:600}
.geo-case small{display:block;margin-top:2px;font-size:10px;color:var(--hv-color-muted-foreground)}
.geo-reset:focus-visible,.geo-case:focus-visible,.geo-footer summary:focus-visible{outline:2px solid #60a5fa;outline-offset:3px}
.geo-active{margin-top:16px}
.geo-active h3{margin:5px 0 0;font-size:16px;line-height:1.35;font-weight:600}
.geo-active>p{margin:6px 0 0;color:var(--hv-color-muted-foreground);font-size:11px}
.geo-table{width:100%;border-collapse:collapse;table-layout:fixed;margin-top:10px;font-variant-numeric:tabular-nums}
.geo-table th,.geo-table td{padding:9px 5px;border-bottom:1px solid var(--hv-color-border);text-align:center}
.geo-table thead th{font-size:10px;font-weight:500;color:var(--hv-color-muted-foreground);vertical-align:bottom;line-height:1.3}
.geo-table th:first-child{width:40%;text-align:left;padding-left:0}
.geo-table tbody th{font-size:11px;font-weight:600;line-height:1.35}
.geo-table td{font-size:17px;font-weight:650}
.geo-table td small{font-size:10px;font-weight:400;color:var(--hv-color-muted-foreground)}
.geo-hyper{color:#60a5fa}.geo-clip{color:#fbbf24}
.geo-definition{margin:8px 0 0;color:var(--hv-color-muted-foreground);font-size:10px}
.geo-result{margin-top:15px;border-left:2px solid #60a5fa;padding:8px 10px;background:var(--hv-color-surface-muted);border-radius:0 5px 5px 0;font-size:12px}
.geo-map-hint{margin:15px 0 0;color:var(--hv-color-muted-foreground);font-size:11px}
.geo-footer{margin-top:16px;padding-top:12px;border-top:1px solid var(--hv-color-border);color:var(--hv-color-muted-foreground);font-size:11px}
.geo-footer summary{cursor:pointer;color:var(--hv-color-foreground);font-weight:500}
.geo-footer p{margin:10px 0 0;overflow-wrap:anywhere}
.geo-footer .geo-table th:first-child{width:42%}
.geo-footer .geo-table td{font-size:12px}
.geo-error{margin-top:10px;color:#f87171;font-size:11px}
.geo-status{margin-top:8px;color:var(--hv-color-muted-foreground);font-size:11px}
@container(max-width:300px){.geo-table th:first-child{width:35%}.geo-table tbody th{font-size:10px}.geo-table td{font-size:15px}}
`;

const readable = (value) => String(value || "").replaceAll("_", " ");
const percent = (value) => Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "—";
const groups = { transport: "Transport", agriculture_vegetation: "Vegetation & farmland", built_environment: "Built environment" };

function rankedProps(model, modelLabel, k) {
  return { mode: "ranked", rank: {
    anchorSampleId: model.anchorSampleId, layoutKey: model.layoutKey,
    k, source: `${modelLabel} · aerial neighbours`, showDistance: false,
  } };
}

export default function GeospatialAuditPanel() {
  const { props = {}, state = {}, patchState } = usePanelState();
  const { updateProps } = usePanelActions();
  const { setSelection, clearSelection } = useSelection();
  const cases = Array.isArray(props.cases) ? props.cases : [];
  const panelIds = props.panelIds || {};
  const models = props.models || {};
  const neighbourK = Number(props.neighbourK) || 10;
  const initialId = props.initialCaseId || cases[0]?.id;
  const active = cases.find((item) => item.id === (state.activeCaseId || initialId)) || cases[0];
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);

  const run = React.useCallback(async (operation) => {
    setBusy(true); setError(null);
    try { await operation(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setBusy(false); }
  }, []);

  const presentCase = React.useCallback((item) => void run(async () => {
    await updateProps(panelIds.hyper3Samples || "hyper3-neighbours", rankedProps({
      anchorSampleId: item.anchorSampleId, layoutKey: item.models.hyper3.layoutKey,
    }, models.hyper3 || "Hyper3-CLIP V1", neighbourK));
    await updateProps(panelIds.clipSamples || "clip-neighbours", rankedProps({
      anchorSampleId: item.anchorSampleId, layoutKey: item.models.clip.layoutKey,
    }, models.clip || "CLIP", neighbourK));
    await patchState({ activeCaseId: item.id });
    await setSelection([item.anchorSampleId]);
  }), [models.clip, models.hyper3, neighbourK, panelIds.clipSamples, panelIds.hyper3Samples, patchState, run, setSelection, updateProps]);

  const reset = () => {
    const first = cases.find((item) => item.id === initialId) || cases[0];
    if (first) presentCase(first); else void run(() => clearSelection());
  };
  if (!active) return <Panel><div className="geo-root">No example is available.</div></Panel>;
  const aggregate = props.aggregate || {};

  return <Panel><div className="geo-root">
    <style aria-hidden="true">{css}</style>
    <header className="geo-header">
      <div><span className="geo-kicker">Aerial image retrieval</span><h2>Which tiles belong together?</h2></div>
      <button type="button" className="geo-reset" disabled={busy} onClick={reset}>Reset</button>
    </header>
    <p className="geo-intro">Compare Hyper3-CLIP V1 and OpenAI CLIP using the same aerial tile and its 10 nearest neighbours.</p>
    <p className="geo-scope">60 curated tiles · 12 classes · saved results</p>

    <section className="geo-section" aria-label="Choose an example">
      <span className="geo-kicker">1 · Choose an example</span>
      <nav className="geo-cases" aria-label="Example tiles">
        {cases.map((item) => <button key={item.id} type="button" className="geo-case" aria-pressed={item.id === active.id} disabled={busy} onClick={() => presentCase(item)}>
          <strong>{item.kind === "Industrial" ? "Storage tanks" : item.kind}</strong>
          <small>{groups[item.parentGroup] || readable(item.parentGroup)}</small>
        </button>)}
      </nav>
    </section>

    <section className="geo-active" aria-label="Selected tile comparison">
      <span className="geo-kicker">2 · Compare the neighbours</span>
      <h3>{active.kind === "Industrial" ? "Storage tanks" : active.kind}</h3>
      <p>{active.question}</p>
      <table className="geo-table" aria-label="Matches among ten neighbours">
        <thead><tr><th scope="col">Model</th><th scope="col">Same<br/>class</th><th scope="col">Same<br/>group</th><th scope="col">Other<br/>group</th></tr></thead>
        <tbody>{["hyper3", "clip"].map((key) => <tr key={key}>
          <th scope="row" className={key === "hyper3" ? "geo-hyper" : "geo-clip"}>{key === "hyper3" ? models.hyper3 : "CLIP ViT-B/32"}</th>
          <td>{active.models[key].exactHits}<small>/{neighbourK}</small></td>
          <td>{active.models[key].parentHits}<small>/{neighbourK}</small></td>
          <td>{active.models[key].offGroupHits}<small>/{neighbourK}</small></td>
        </tr>)}</tbody>
      </table>
      <p className="geo-definition">Four same-class tiles are available. Same group includes same-class matches.</p>
      <div className="geo-result" role="status" aria-live="polite">{active.comparison}</div>
    </section>

    <p className="geo-map-hint">Open the archive-map tabs to explore all 60 tiles.</p>
    <details className="geo-footer">
      <summary>Evaluation scope &amp; results</summary>
      <p>{props.protocol?.subset}. Each tile is used as an anchor; self-matches are excluded. {props.protocol?.claimBoundary}</p>
      <table className="geo-table" aria-label="Average precision at ten across sixty tiles">
        <thead><tr><th scope="col">Average P@10</th><th scope="col" className="geo-hyper">Hyper3 V1</th><th scope="col" className="geo-clip">CLIP</th></tr></thead>
        <tbody><tr><th scope="row">Same class</th><td>{percent(aggregate.hyper3?.exactP10)}</td><td>{percent(aggregate.clip?.exactP10)}</td></tr>
          <tr><th scope="row">Same group</th><td>{percent(aggregate.hyper3?.parentP10)}</td><td>{percent(aggregate.clip?.parentP10)}</td></tr></tbody>
      </table>
      <p>{props.protocol?.metricDefinition}</p>
      <p>Groups: transport (aircraft, airports, runways, bridges); vegetation &amp; farmland (forest, meadow, circular and rectangular farmland, terraces); built environment (storage tanks, basketball courts, sparse residential).</p>
      <p>Neighbours use Hyper3 hyperbolic distance and CLIP cosine distance. Compare ranks; distances are not on a shared scale. The 2D archive maps are projections, not the space used for retrieval.</p>
      <p>Hyper3-CLIP V1 · {props.provenance?.hyper3?.repo} · revision {props.provenance?.hyper3?.revision?.slice(0, 12)}. {props.protocol?.modelRevisionCaveat}</p>
      <p>{props.protocol?.sourceCaveat} This viewer shows prepared image neighbours; it does not run new text queries.</p>
    </details>
    {busy ? <div className="geo-status">Updating neighbours…</div> : null}
    {error ? <div className="geo-error" role="alert">{error}</div> : null}
  </div></Panel>;
}
