const sdk = globalThis.HyperViewPanelSDK;
if (!sdk || sdk.version !== "2") {
  throw new Error("HyperViewPanelSDK v2 is not available on window.");
}

const { React, hooks } = sdk;
const { usePanelActions, usePanelState, useSample, useSampleResults, useSelection } = hooks;

function mediaUrl(sample) {
  const raw = sample?.media_url || sample?.thumbnail_url || sample?.thumbnail;
  return typeof raw === "string" && raw ? raw : null;
}

function RankCard({ name, color, rank }) {
  const consequence = rank === 1
    ? "Found first"
    : rank <= 5
      ? `Visible at #${rank}`
      : `${rank - 1} regions appear first`;
  return (
    <article className="pr-rank-card">
      <div><i style={{ background: color }} />{name}</div>
      <strong style={{ color }}>#{rank}</strong>
      <small>{consequence}</small>
    </article>
  );
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

  const chooseCase = (item) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        await showResults(
          item.results.hyper3.map((result) => result.sampleId),
          { focus: false, source: `${item.shortLabel} · Hyper3-CLIP · Top 5` },
        );
        await updateProps("precision-clip-results", { mode: "results", collectionId: item.collectionIds.clip });
        await patchState({ activeCaseId: item.id });
        await setSelection([item.targetSampleId]);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : String(reason));
      } finally {
        setBusy(false);
      }
    })();
  };

  if (!active) return <main className="pr-root">No Precision Regions cases are available.</main>;

  const sourceUrl = mediaUrl(source);
  const targetUrl = mediaUrl(target);
  const benchmark = props.benchmark || {};

  return (
    <main className="pr-root">
      <style>{`
        .pr-root,.pr-root *{box-sizing:border-box}.pr-root{height:100%;overflow:auto;padding:14px;color:var(--hv-color-foreground);background:var(--hv-color-background);font:11px/1.42 system-ui,-apple-system,BlinkMacSystemFont,sans-serif}.pr-kicker{display:block;color:var(--hv-color-muted-foreground);font-size:9px;font-weight:800;letter-spacing:.09em;text-transform:uppercase}.pr-header h2{margin:3px 0 0;font-size:18px;line-height:1.15;letter-spacing:-.02em}.pr-header p{margin:6px 0 0;color:var(--hv-color-muted-foreground)}.pr-query{margin:12px 0 0;padding:9px 10px;border-left:2px solid var(--hv-color-accent);background:var(--hv-color-surface-muted);font-size:13px;font-weight:680}.pr-visual{position:relative;margin-top:10px;min-height:176px;overflow:hidden;border:1px solid var(--hv-color-border);border-radius:9px;background:var(--hv-color-surface-muted);cursor:pointer}.pr-visual>img{display:block;width:100%;height:210px;object-fit:cover}.pr-crop{position:absolute;right:8px;bottom:8px;width:86px;height:86px;padding:4px;border:1px solid rgba(255,255,255,.8);border-radius:7px;background:rgba(8,12,18,.9);box-shadow:0 5px 20px rgba(0,0,0,.35)}.pr-crop img{width:100%;height:100%;object-fit:contain}.pr-crop span,.pr-visual-label{position:absolute;border-radius:4px;padding:3px 6px;background:rgba(8,12,18,.82);color:white;font-size:8px;font-weight:800;text-transform:uppercase;letter-spacing:.06em}.pr-visual-label{left:8px;top:8px}.pr-crop span{right:3px;bottom:3px}.pr-ranks{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px}.pr-rank-card{border:1px solid var(--hv-color-border);border-radius:8px;padding:9px;background:var(--hv-color-surface)}.pr-rank-card div{display:flex;align-items:center;gap:5px;font-weight:720}.pr-rank-card i{width:7px;height:7px;border-radius:99px}.pr-rank-card strong{display:block;margin-top:2px;font-size:18px}.pr-rank-card small{display:block;color:var(--hv-color-muted-foreground);font-size:9px}.pr-cases{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:10px}.pr-case{min-width:0;border:1px solid var(--hv-color-border);border-radius:7px;padding:7px 6px;background:var(--hv-color-surface);color:var(--hv-color-foreground);text-align:left;cursor:pointer}.pr-case[aria-pressed=true]{border-color:var(--hv-color-accent);box-shadow:inset 0 0 0 1px var(--hv-color-accent)}.pr-case strong,.pr-case small{display:block;overflow:hidden;text-overflow:ellipsis}.pr-case strong{font-size:9px}.pr-case small{margin-top:2px;color:var(--hv-color-muted-foreground);font-size:8px}.pr-benchmark{margin-top:13px;border-top:1px solid var(--hv-color-border);padding-top:10px}.pr-benchmark h3{margin:3px 0 2px;font-size:12px}.pr-caption{margin:0 0 7px;color:var(--hv-color-muted-foreground);font-size:9px}.pr-table{width:100%;border-collapse:collapse;font-size:9px}.pr-table th,.pr-table td{padding:5px 4px;border-bottom:1px solid var(--hv-color-border);text-align:right}.pr-table th:first-child,.pr-table td:first-child{text-align:left}.pr-table th{color:var(--hv-color-muted-foreground);font-size:8px;text-transform:uppercase}.pr-note{margin:7px 0 0;color:var(--hv-color-muted-foreground);font-size:9px}.pr-error{color:#ef4444}.pr-busy{opacity:.62}@media(max-width:390px){.pr-root{padding:10px}.pr-ranks{grid-template-columns:1fr}.pr-visual>img{height:180px}}
      `}</style>

      <header className="pr-header">
        <span className="pr-kicker">Language-guided region search</span>
        <h2>Which region matches the description?</h2>
        <p>Compare where the boxed region appears in each result list.</p>
      </header>

      <blockquote className="pr-query">“{active.query}”</blockquote>

      <button type="button" className="pr-visual" onClick={() => void setSelection([active.targetSampleId])}>
        {sourceUrl ? <img src={sourceUrl} alt={`${active.shortLabel} source scene`} /> : null}
        <span className="pr-visual-label">The object in context</span>
        <span className="pr-crop">
          {targetUrl ? <img src={targetUrl} alt={active.query || "Target crop"} /> : null}
          <span>Target</span>
        </span>
      </button>

      <section className="pr-ranks" aria-label="Exact target ranks">
        <RankCard name="Hyper3-CLIP" color="#60a5fa" rank={active.target.hyper3Rank} />
        <RankCard name="OpenAI CLIP" color="#f59e0b" rank={active.target.clipRank} />
      </section>
      <p className="pr-note">Each list shows the top five regions from the shared cross-image pool. A target ranked below five is outside that visible shortlist.</p>

      <nav className="pr-cases" aria-label="Object search examples">
        {cases.map((item) => (
          <button key={item.id} type="button" className={`pr-case${busy ? " pr-busy" : ""}`} aria-pressed={item.id === active.id} disabled={busy} onClick={() => chooseCase(item)}>
            <strong>{item.shortLabel}</strong><small>{item.context}</small>
          </button>
        ))}
      </nav>

      <section className="pr-benchmark" aria-label="Full benchmark results">
        <span className="pr-kicker">How the models compare</span>
        <h3>RefCOCOg · {benchmark.queryCount || 180} descriptions</h3>
        <p className="pr-caption">One correct region per description in this 180-description diagnostic subset.</p>
        <table className="pr-table"><thead><tr><th>Correct region</th><th style={{color:"#60a5fa"}}>Hyper3</th><th style={{color:"#f59e0b"}}>CLIP</th></tr></thead><tbody>
          <tr><td>Ranked first</td><td>{benchmark.hyper3Hit1}</td><td>{benchmark.clipHit1}</td></tr>
          <tr><td>Within top ten</td><td>{benchmark.hyper3Hit10}</td><td>{benchmark.clipHit10}</td></tr>
          <tr><td>Average rank score</td><td>{benchmark.hyper3Mrr}</td><td>{benchmark.clipMrr}</td></tr>
        </tbody></table>
        <p className="pr-note">The examples are diagnostic rank-separation cases; the table covers the full subset and is descriptive, not a significance claim.</p>
      </section>

      {sourceError || targetError ? <div className="pr-error">{sourceError || targetError}</div> : null}
      {error ? <div className="pr-error" role="alert">{error}</div> : null}
    </main>
  );
}
