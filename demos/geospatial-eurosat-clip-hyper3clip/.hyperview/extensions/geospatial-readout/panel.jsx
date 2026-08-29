const sdk = globalThis.HyperViewPanelSDK;
if (!sdk || sdk.version !== "2") {
  throw new Error("HyperViewPanelSDK v2 is required.");
}

const { React, hooks } = sdk;
const { usePanelActions, usePanelState, useSelection } = hooks;

const css = `
*{box-sizing:border-box}
.geo-root{height:100%;min-height:0;overflow:auto;overscroll-behavior:contain;padding:12px 13px;color:var(--hv-color-foreground);background:var(--hv-color-background);font:11px/1.4 system-ui,-apple-system,BlinkMacSystemFont,sans-serif}
.geo-kicker{display:block;color:var(--hv-color-muted-foreground);font-size:9px;font-weight:800;letter-spacing:.09em;text-transform:uppercase}
.geo-header{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.geo-header h2{margin:3px 0 0;font-size:16px;line-height:1.15;letter-spacing:-.02em}
.geo-header p{margin:6px 0 0;color:var(--hv-color-muted-foreground);font-size:10px}
.geo-reset{flex:0 0 auto;border:1px solid var(--hv-color-border);border-radius:6px;padding:5px 8px;color:var(--hv-color-foreground);background:var(--hv-color-surface-muted);cursor:pointer;font-size:10px}
.geo-reset:disabled,.geo-case:disabled{opacity:.55;cursor:wait}
.geo-questions{margin:10px 0 0;padding:0;list-style:none;display:grid;gap:5px}
.geo-questions li{border-left:2px solid var(--hv-color-accent);padding:4px 0 4px 8px;color:var(--hv-color-muted-foreground);font-size:10px}
.geo-aggregate{margin-top:11px;border:1px solid var(--hv-color-border);border-radius:8px;overflow:hidden;background:var(--hv-color-surface)}
.geo-aggregate-head{display:flex;justify-content:space-between;gap:8px;padding:6px 8px;border-bottom:1px solid var(--hv-color-border);color:var(--hv-color-muted-foreground);font-size:9px}
.geo-metrics{display:grid;grid-template-columns:1fr 1fr}
.geo-metric{padding:7px 8px}
.geo-metric+.geo-metric{border-left:1px solid var(--hv-color-border)}
.geo-metric span{display:block;color:var(--hv-color-muted-foreground);font-size:8px;text-transform:uppercase;letter-spacing:.05em}
.geo-metric strong{display:block;margin-top:3px;font-size:11px}
.geo-hyper{color:#60a5fa}.geo-clip{color:#f59e0b}
.geo-cases{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:11px}
.geo-case{min-width:0;border:1px solid var(--hv-color-border);border-radius:7px;padding:7px 8px;color:var(--hv-color-muted-foreground);background:var(--hv-color-surface);cursor:pointer;text-align:left}
.geo-case[aria-pressed=true]{border-color:var(--hv-color-accent);color:var(--hv-color-foreground);box-shadow:inset 3px 0 var(--hv-color-accent);background:color-mix(in srgb,var(--hv-color-accent) 10%,var(--hv-color-surface))}
.geo-case small,.geo-case strong{display:block;overflow:hidden}
.geo-case small{font-size:8px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}
.geo-case strong{min-height:2.5em;margin-top:2px;font-size:11px;line-height:1.25}
.geo-active{margin-top:11px;border:1px solid var(--hv-color-border);border-radius:8px;padding:9px;background:var(--hv-color-surface)}
.geo-active h3{margin:3px 0 0;font-size:13px;line-height:1.3}
.geo-facts{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}
.geo-pill{border:1px solid var(--hv-color-border);border-radius:999px;padding:2px 6px;color:var(--hv-color-muted-foreground);font-size:8px}
.geo-models{display:grid;gap:7px;margin-top:10px}
.geo-model{border:1px solid var(--hv-color-border);border-radius:8px;padding:8px;background:var(--hv-color-surface)}
.geo-model-head{display:flex;align-items:center;justify-content:space-between;gap:8px;font-weight:780}
.geo-model-head span{display:flex;align-items:center;gap:5px;min-width:0}
.geo-model-head i{width:7px;height:7px;border-radius:99px;flex:0 0 auto}
.geo-counts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;margin-top:7px}
.geo-count{border:1px solid var(--hv-color-border);border-radius:6px;padding:5px 6px;background:var(--hv-color-surface-muted)}
.geo-count small{display:block;color:var(--hv-color-muted-foreground);font-size:8px;text-transform:uppercase;letter-spacing:.04em}
.geo-count strong{display:block;margin-top:2px;font-size:13px}
.geo-count.is-exact strong{color:#22c55e}
.geo-count.is-parent strong{color:#60a5fa}
.geo-count.is-off strong{color:#f59e0b}
.geo-model p,.geo-compare p{margin:7px 0 0;color:var(--hv-color-muted-foreground);font-size:10px;line-height:1.4}
.geo-compare{margin-top:9px;border-left:2px solid var(--hv-color-accent);padding:6px 8px;background:var(--hv-color-surface-muted);border-radius:0 6px 6px 0}
.geo-compare strong{display:block;font-size:10px}
.geo-hint{margin:10px 0 0;color:var(--hv-color-muted-foreground);font-size:9px;line-height:1.4}
.geo-footer{margin-top:11px;padding-top:8px;border-top:1px solid var(--hv-color-border);color:var(--hv-color-muted-foreground);font-size:9px}
.geo-footer summary{cursor:pointer}
.geo-footer p{margin:6px 0 0;max-width:360px}
.geo-error{margin-top:8px;color:#ef4444;font-size:10px}
.geo-status{margin-top:6px;color:var(--hv-color-muted-foreground);font-size:9px}
@media(max-width:420px){
  .geo-root{padding:10px}
  .geo-cases{grid-template-columns:1fr}
  .geo-metrics{grid-template-columns:1fr}
  .geo-metric+.geo-metric{border-left:0;border-top:1px solid var(--hv-color-border)}
}
`;

function readable(value) {
  return String(value || "").replaceAll("_", " ");
}

function percent(value) {
  return Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "—";
}

function modelColor(modelKey) {
  return modelKey === "hyper3" ? "#60a5fa" : "#f59e0b";
}

function rankedProps(model, modelLabel, k) {
  return {
    mode: "ranked",
    rank: {
      anchorSampleId: model.anchorSampleId,
      layoutKey: model.layoutKey,
      k: k || 10,
      source: `${modelLabel} · aerial neighbours`,
      showDistance: false,
    },
  };
}

function CountCell({ kind, label, value }) {
  return (
    <div className={`geo-count is-${kind}`}>
      <small>{label}</small>
      <strong>{value}/10</strong>
    </div>
  );
}

export default function GeospatialAuditPanel() {
  const { props = {}, state = {}, patchState } = usePanelState();
  const { updateProps } = usePanelActions();
  const { selectedIds, setSelection, clearSelection } = useSelection();
  const cases = Array.isArray(props.cases) ? props.cases : [];
  const panelIds = props.panelIds || {};
  const models = props.models || {};
  const neighbourK = Number(props.neighbourK) || 10;
  const initialId = props.initialCaseId || cases[0]?.id;
  const activeId = state.activeCaseId || initialId;
  const active = cases.find((item) => item.id === activeId) || cases[0] || null;
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);

  const run = React.useCallback(async (operation) => {
    setBusy(true);
    setError(null);
    try {
      await operation();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }, []);

  const presentCase = React.useCallback(
    (item) =>
      void run(async () => {
        const hyper3Panel = panelIds.hyper3Samples || "hyper3-neighbours";
        const clipPanel = panelIds.clipSamples || "clip-neighbours";
        await updateProps(
          hyper3Panel,
          rankedProps(
            {
              anchorSampleId: item.anchorSampleId,
              layoutKey: item.models.hyper3.layoutKey,
            },
            models.hyper3 || "Hyper3-CLIP",
            neighbourK,
          ),
        );
        await updateProps(
          clipPanel,
          rankedProps(
            {
              anchorSampleId: item.anchorSampleId,
              layoutKey: item.models.clip.layoutKey,
            },
            models.clip || "CLIP",
            neighbourK,
          ),
        );
        await patchState({ activeCaseId: item.id });
        await setSelection([item.anchorSampleId]);
      }),
    [
      models.clip,
      models.hyper3,
      neighbourK,
      panelIds.clipSamples,
      panelIds.hyper3Samples,
      patchState,
      run,
      setSelection,
      updateProps,
    ],
  );

  const reset = () => {
    const first = cases.find((item) => item.id === initialId) || cases[0];
    if (first) presentCase(first);
    else void run(() => clearSelection());
  };

  if (!active) {
    return (
      <main className="geo-root">
        <style aria-hidden="true">{css}</style>
        No GeoSpatial case is available.
      </main>
    );
  }

  const aggregate = props.aggregate || {};
  return (
    <main className="geo-root">
      <style aria-hidden="true">{css}</style>

      <header className="geo-header">
        <div>
          <span className="geo-kicker">Aerial image retrieval</span>
          <h2>Which tiles belong together?</h2>
          <p>Choose a tile and compare its ten nearest neighbours.</p>
        </div>
        <button
          type="button"
          className="geo-reset"
          disabled={busy}
          onClick={reset}
        >
          Reset
        </button>
      </header>

      <nav className="geo-cases" aria-label="Example tiles">
        {cases.map((item) => (
          <button
            key={item.id}
            type="button"
            className="geo-case"
            aria-pressed={item.id === active.id}
            disabled={busy}
            onClick={() => presentCase(item)}
          >
            <small>{item.kind}</small>
            <strong>{item.title}</strong>
          </button>
        ))}
      </nav>
      <section className="geo-active" aria-label="Selected tile">
        <span className="geo-kicker">Selected tile</span>
        <h3>{active.question}</h3>
        <div className="geo-facts">
          <span className="geo-pill">Exact: {readable(active.exactClass)}</span>
          <span className="geo-pill">
            Parent: {readable(active.parentGroup)}
          </span>
        </div>

        <div className="geo-models" aria-label="Model identity counts">
          {["hyper3", "clip"].map((modelKey) => {
            const model = active.models[modelKey] || {};
            return (
              <article className="geo-model" key={modelKey}>
                <div className="geo-model-head">
                  <span>
                    <i style={{ background: modelColor(modelKey) }} />
                    <span className={modelKey === "hyper3" ? "geo-hyper" : "geo-clip"}>
                      {models[modelKey] || modelKey}
                    </span>
                  </span>
                  <span className="geo-kicker">Top {neighbourK}</span>
                </div>
                <div className="geo-counts">
                  <CountCell
                    kind="exact"
                    label="Exact (max 4)"
                    value={model.exactHits ?? "—"}
                  />
                  <CountCell
                    kind="parent"
                    label="Same group (incl. exact)"
                    value={model.parentHits ?? "—"}
                  />
                  <CountCell
                    kind="off"
                    label="Off-group"
                    value={model.offGroupHits ?? "—"}
                  />
                </div>
                <p>{model.consequence}</p>
              </article>
            );
          })}
        </div>
      </section>

      {active.comparison ? (
        <div className="geo-compare">
          <strong>What this means</strong>
          <p>{active.comparison}</p>
        </div>
      ) : null}

      <p className="geo-hint">Open each archive map to inspect clusters and outliers. Compare rank rather than distance because the models use different geometries.</p>

      <section className="geo-aggregate" aria-label="Aggregate retrieval results">
        <div className="geo-aggregate-head">
          <strong>Across all {props.workspaceSampleCount || 60} tiles</strong>
          <span>Precision at 10</span>
        </div>
        <div className="geo-metrics">
          <div className="geo-metric"><span>Same class (4 available per query)</span><strong><span className="geo-hyper">H3 {percent(aggregate.hyper3?.exactP10)}</span>{" · "}<span className="geo-clip">CLIP {percent(aggregate.clip?.exactP10)}</span></strong></div>
          <div className="geo-metric"><span>Same land-use group</span><strong><span className="geo-hyper">H3 {percent(aggregate.hyper3?.parentP10)}</span>{" · "}<span className="geo-clip">CLIP {percent(aggregate.clip?.parentP10)}</span></strong></div>
        </div>
      </section>

      <details className="geo-footer">
        <summary>Evaluation scope</summary>
        <p>{props.protocol?.dataset} · {props.protocol?.split} · {props.protocol?.subset}. {props.protocol?.claimBoundary}</p>
      </details>

      {busy ? <div className="geo-status">Updating ranked neighbours…</div> : null}
      {error ? (
        <div className="geo-error" role="alert">
          {error}
        </div>
      ) : null}
    </main>
  );
}
