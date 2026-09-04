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
const { usePanelState, useSampleResults, useSelection } = hooks;

function modelColor(modelKey) {
  return modelKey === "hyper3" ? "#60a5fa" : "#f59e0b";
}

function orderedIds(item, modelKey) {
  return [...(item?.results?.[modelKey] || [])]
    .sort((left, right) => Number(left.rank) - Number(right.rank))
    .map((result) => result.sampleId);
}

function visibleTargetIds(item, modelKey) {
  return (item?.results?.[modelKey] || []).some((result) => result.isTarget)
    ? [item.target.sampleId]
    : [];
}

function percentage(value) {
  const parsed = Number.parseFloat(String(value ?? ""));
  return Number.isFinite(parsed) ? parsed : null;
}

export default function LogoBriefDesk() {
  const { props = {}, state = {}, patchState } = usePanelState();
  const { showResults, resetResults } = useSampleResults();
  const { setSelection } = useSelection();
  const cases = Array.isArray(props.cases) ? props.cases : [];
  const active = cases.find((item) => item.id === state.activeCaseId) || cases[0] || null;
  const activeModelKey = state.activeModelKey === "clip" ? "clip" : "hyper3";
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);
  const sampleCount = Number(props.workspaceSampleCount) || 160;

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

  const present = (item, modelKey = activeModelKey) =>
    void run(async () => {
      const modelName = props.models?.[modelKey] || modelKey;
      await showResults(orderedIds(item, modelKey), {
        focus: false,
        source: `${modelName} · ${item.label} · Top 5 of ${sampleCount} logos`,
      });
      await setSelection(visibleTargetIds(item, modelKey));
      await patchState({ activeCaseId: item.id, activeModelKey: modelKey });
    });

  if (!active) {
    return <Panel><div className="lb-root">No Logo Search cases are available.</div></Panel>;
  }

  const rank =
    activeModelKey === "hyper3" ? active.target.hyper3Rank : active.target.clipRank;
  const aggregate = props.aggregate || {};
  const hyper3Hit1 = percentage(aggregate.hyper3Hit1);
  const clipHit1 = percentage(aggregate.clipHit1);
  const firstRankRatio =
    hyper3Hit1 !== null && clipHit1 !== null && clipHit1 > 0
      ? (hyper3Hit1 / clipHit1).toFixed(1)
      : null;

  return (
    <Panel>
      <div className="lb-root">
        <style>{`
          .lb-root,.lb-root *{box-sizing:border-box}
          .lb-root{flex:1;min-height:0;overflow:auto;padding:12px 13px;background:var(--hv-color-background);color:var(--hv-color-foreground);font:11px/1.45 system-ui,-apple-system,BlinkMacSystemFont,sans-serif}
          .lb-kicker{display:block;color:var(--hv-color-muted-foreground);font-size:9px;font-weight:800;letter-spacing:.09em;text-transform:uppercase}
          .lb-header h2{margin:3px 0 0;font-size:17px;line-height:1.15;letter-spacing:-.02em}
          .lb-header p{margin:6px 0 0;color:var(--hv-color-muted-foreground)}
          .lb-cases{display:grid;gap:5px;margin-top:10px}
          .lb-case{border:1px solid var(--hv-color-border);border-radius:7px;padding:7px 8px;background:var(--hv-color-surface);color:var(--hv-color-foreground);text-align:left;cursor:pointer}
          .lb-case[aria-pressed=true]{border-color:var(--hv-color-accent);box-shadow:inset 0 0 0 1px var(--hv-color-accent)}
          .lb-case strong,.lb-case small{display:block}
          .lb-case small{margin-top:2px;color:var(--hv-color-muted-foreground);font-size:9px}
          .lb-query{margin-top:10px;border-top:1px solid var(--hv-color-border);padding-top:9px}
          .lb-query details{margin-top:7px;color:var(--hv-color-muted-foreground);font-size:9px}.lb-query summary{cursor:pointer}.lb-query blockquote{margin:6px 0 0;font-size:10px;line-height:1.4}
          .lb-attrs{display:grid;gap:3px;margin-top:8px}
          .lb-attr{display:grid;grid-template-columns:72px minmax(0,1fr);gap:6px;padding-top:3px;border-top:1px solid color-mix(in srgb,var(--hv-color-border) 70%,transparent)}
          .lb-attr dt{color:var(--hv-color-muted-foreground);font-size:8px;text-transform:uppercase}
          .lb-attr dd{margin:0;font-size:10px}
          .lb-business{margin:8px 0 0;color:var(--hv-color-muted-foreground);font-size:10px}
          .lb-models{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:10px}
          .lb-model{border:1px solid var(--hv-color-border);border-radius:8px;padding:8px;background:var(--hv-color-surface);color:var(--hv-color-foreground);text-align:left;cursor:pointer}
          .lb-model.is-active{border-color:var(--hv-color-accent);box-shadow:inset 0 0 0 1px var(--hv-color-accent)}
          .lb-model-top{display:flex;justify-content:space-between;gap:6px;font-weight:760}
          .lb-model-top span{display:flex;align-items:center;gap:5px}
          .lb-model-top i{width:7px;height:7px;border-radius:99px}
          .lb-model-top strong{font-size:15px}
          .lb-model small{display:block;margin-top:2px;color:var(--hv-color-muted-foreground);font-size:8px}
          .lb-model p{margin:6px 0 0;color:var(--hv-color-muted-foreground);font-size:9px}
          .lb-active-proof{margin-top:9px;border-left:2px solid var(--hv-color-accent);padding:6px 8px;background:var(--hv-color-surface-muted);font-size:10px}
          .lb-actions{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px}
          .lb-action{border:1px solid var(--hv-color-border);border-radius:6px;padding:6px 8px;background:var(--hv-color-surface-muted);color:var(--hv-color-foreground);cursor:pointer;font-size:10px}
          .lb-note,.lb-footer{color:var(--hv-color-muted-foreground);font-size:9px}
          .lb-note{margin-top:9px}
          .lb-footer{margin-top:10px;border-top:1px solid var(--hv-color-border);padding-top:8px}
          .lb-error{color:#ef4444}
          .lb-busy{opacity:.62}
          .lb-benchmark{margin-top:12px;border-top:1px solid var(--hv-color-border);padding-top:10px}.lb-benchmark h3{margin:2px 0 7px;font-size:12px}.lb-table{width:100%;border-collapse:collapse;font-size:9px}.lb-table th,.lb-table td{padding:5px 4px;border-bottom:1px solid var(--hv-color-border);text-align:right}.lb-table th:first-child,.lb-table td:first-child{text-align:left}.lb-table th{color:var(--hv-color-muted-foreground);font-size:8px;text-transform:uppercase}.lb-table-note{margin:7px 0 0;color:var(--hv-color-muted-foreground);font-size:9px}
          @media(max-width:420px){.lb-root{padding:10px}.lb-models{grid-template-columns:1fr}}
        `}</style>

        <header className="lb-header">
          <span className="lb-kicker">Creative brief retrieval</span>
          <h2>Which logos make the first review screen?</h2>
          <p>Choose a brief, compare the shortlist, and inspect the catalog’s style coverage.</p>
        </header>

        <nav className="lb-cases" aria-label="Creative briefs">
          {cases.map((item, index) => (
            <button
              key={item.id}
              type="button"
              className={`lb-case${busy ? " lb-busy" : ""}`}
              aria-pressed={item.id === active.id}
              disabled={busy}
              onClick={() => present(item)}
            >
              <span className="lb-kicker">
                Brief {String(index + 1).padStart(2, "0")} · {item.shortLabel}
              </span>
              <strong>{item.label}</strong>
              <small>
                Exact target: H3 #{item.target.hyper3Rank} · CLIP #{item.target.clipRank}
              </small>
            </button>
          ))}
        </nav>

        <section className="lb-query">
          <span className="lb-kicker">Creative brief</span>
          <dl className="lb-attrs" aria-label="Brief attributes">
            {active.attributes.map((item) => (
              <div className="lb-attr" key={item.label}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>
          <p className="lb-business">{active.business}</p>
          <details>
            <summary>Original catalog caption</summary>
            <blockquote>“{active.query}”</blockquote>
          </details>
        </section>

        <section className="lb-models" aria-label="Model result sets">
          {["hyper3", "clip"].map((modelKey) => {
            const modelRank =
              modelKey === "hyper3" ? active.target.hyper3Rank : active.target.clipRank;
            return (
              <button
                key={modelKey}
                type="button"
                className={`lb-model${activeModelKey === modelKey ? " is-active" : ""}`}
                disabled={busy}
                onClick={() => present(active, modelKey)}
              >
                <span className="lb-model-top">
                  <span>
                    <i style={{ background: modelColor(modelKey) }} />
                    {props.models?.[modelKey]}
                  </span>
                  <strong style={{ color: modelColor(modelKey) }}>#{modelRank}</strong>
                </span>
                <small>exact asset rank · top 5 of {sampleCount} logos</small>
                <p>{active.modelReadout[modelKey]}</p>
              </button>
            );
          })}
        </section>

        <div className="lb-active-proof">
          <strong>{props.models?.[activeModelKey]} result set</strong>
          <br />
          Exact target rank #{rank} of {sampleCount}. {rank <= 5 ? "The target is marked in the shortlist." : "The target is outside the visible shortlist."}
        </div>

        <div className="lb-actions">
          <button
            type="button"
            className="lb-action"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                await showResults([active.target.sampleId], {
                  focus: false,
                  source: `${active.label} · exact target`,
                });
                await setSelection([active.target.sampleId]);
              })
            }
          >
            Show exact target
          </button>
          <button
            type="button"
            className="lb-action"
            disabled={busy}
            onClick={() =>
              void run(async () => {
                await resetResults({ focus: false, source: "logo-brief-desk" });
                await setSelection([]);
              })
            }
          >
            Browse all {sampleCount} logos
          </button>
        </div>

        <p className="lb-note">The map shows visual and style families across all {sampleCount} logos.</p>

        <section className="lb-benchmark" aria-label="Full benchmark results">
          <span className="lb-kicker">Full benchmark</span>
          <h3>
            {firstRankRatio
              ? `Hyper3 ranks the exact logo first ${firstRankRatio}× as often`
              : "How often does the exact logo reach the first screen?"}
          </h3>
          <table className="lb-table">
            <thead><tr><th>Exact logo found</th><th style={{color:"#60a5fa"}}>Hyper3</th><th style={{color:"#f59e0b"}}>CLIP</th></tr></thead>
            <tbody>
              <tr><td>Ranked first</td><td>{aggregate.hyper3Hit1} ({aggregate.hyper3Hit1Count})</td><td>{aggregate.clipHit1} ({aggregate.clipHit1Count})</td></tr>
              <tr><td>Within top five</td><td>{aggregate.hyper3Hit5} ({aggregate.hyper3Hit5Count})</td><td>{aggregate.clipHit5} ({aggregate.clipHit5Count})</td></tr>
            </tbody>
          </table>
          <p className="lb-table-note">Across {aggregate.queryCount || 160} briefs, each searching the same 160-logo catalog. Mean reciprocal rank improves by {aggregate.mrrDelta}.</p>
        </section>
        <p className="lb-footer">{props.claim}</p>
        {error ? (
          <p className="lb-error" role="alert">
            {error}
          </p>
        ) : null}
      </div>
    </Panel>
  );
}
