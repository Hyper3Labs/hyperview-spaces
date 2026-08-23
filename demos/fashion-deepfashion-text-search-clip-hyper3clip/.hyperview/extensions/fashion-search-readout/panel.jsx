const sdk = globalThis.HyperViewPanelSDK;
if (!sdk || sdk.version !== "2") {
  throw new Error("HyperViewPanelSDK v2 is not available on window.");
}

const { React, hooks } = sdk;
const { usePanelActions, usePanelState, useSampleResults, useSamples, useSelection } = hooks;

function mediaUrl(sample) {
  const raw = sample?.media_url || sample?.thumbnail_url || sample?.thumbnail;
  return typeof raw === "string" && raw ? raw : null;
}

function percentage(value) {
  return Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : "—";
}

function ModelCard({ name, checkpoint, color, rank, readout }) {
  return (
    <article className="fs-model">
      <span className="fs-model-top"><span><i style={{background:color}} />{name}</span><strong style={{color}}>#{rank}</strong></span>
      <small>{checkpoint} · first matching product</small><p>{readout}</p>
    </article>
  );
}

export default function FashionSearchPanel() {
  const { props = {}, state = {}, patchState } = usePanelState();
  const { updateProps } = usePanelActions();
  const { showResults } = useSampleResults();
  const { setSelection } = useSelection();
  const photoCases = Array.isArray(props.photoCases) ? props.photoCases : [];
  const textCases = Array.isArray(props.cases) ? props.cases : [];
  const mode = state.activeMode === "text" ? "text" : "photo";
  const activePhoto = photoCases.find((item) => item.id === state.activePhotoCaseId) || photoCases[0] || null;
  const activeText = textCases.find((item) => item.id === state.activeTextCaseId) || textCases[0] || null;
  const active = mode === "photo" ? activePhoto : activeText;
  const samplePage = useSamples(props.collectionId, { pageSize: 800 });
  const sampleById = React.useMemo(() => new Map(samplePage.samples.map((sample) => [sample.id, sample])), [samplePage.samples]);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (samplePage.hasMore && !samplePage.loading) samplePage.loadMore();
  }, [samplePage.hasMore, samplePage.loading, samplePage.loadMore]);

  const present = (item, nextMode) => {
    if (!item || busy) return;
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        await showResults(
          item.results.hyper3.map((result) => result.sampleId),
          { focus: false, source: `${item.label} · Hyper3-CLIP` },
        );
        const anchorSampleId = nextMode === "photo" ? item.anchorSampleId : null;
        await updateProps("samples", { mode: "results", collectionId: item.collectionIds.hyper3, anchorSampleId });
        await updateProps(props.clipSamplesPanelId || "fashion-clip-results", { mode: "results", collectionId: item.collectionIds.clip, anchorSampleId });
        await patchState(nextMode === "photo" ? { activeMode: "photo", activePhotoCaseId: item.id } : { activeMode: "text", activeTextCaseId: item.id });
        await setSelection([nextMode === "photo" ? item.anchorSampleId : item.target.sampleId]);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : String(reason));
      } finally {
        setBusy(false);
      }
    })();
  };

  if (!active) return <main className="fs-root">No Fashion cases are available.</main>;

  const visualSampleId = mode === "photo" ? active.anchorSampleId : active.target.sampleId;
  const visual = sampleById.get(visualSampleId);
  const visualUrl = mediaUrl(visual);
  const photoBenchmark = props.photoBenchmark || {};
  const typed = props.aggregate || {};
  const models = props.models || {};

  return (
    <main className="fs-root">
      <style>{`
        .fs-root,.fs-root *{box-sizing:border-box}.fs-root{height:100%;overflow:auto;padding:14px;background:var(--hv-color-background);color:var(--hv-color-foreground);font:11px/1.42 system-ui,-apple-system,BlinkMacSystemFont,sans-serif}.fs-kicker{display:block;color:var(--hv-color-muted-foreground);font-size:9px;font-weight:800;letter-spacing:.09em;text-transform:uppercase}.fs-header h2{margin:3px 0 0;font-size:18px;line-height:1.15;letter-spacing:-.02em}.fs-header p{margin:6px 0 0;color:var(--hv-color-muted-foreground)}.fs-tabs{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:11px}.fs-tab{border:1px solid var(--hv-color-border);border-radius:8px;padding:9px 8px;background:var(--hv-color-surface);color:var(--hv-color-muted-foreground);cursor:pointer;font-weight:760}.fs-tab:hover{border-color:color-mix(in srgb,var(--hv-color-accent) 55%,var(--hv-color-border));color:var(--hv-color-foreground)}.fs-tab.is-active{border-color:var(--hv-color-accent);background:color-mix(in srgb,var(--hv-color-accent) 20%,var(--hv-color-surface));color:var(--hv-color-foreground);box-shadow:inset 0 0 0 1px var(--hv-color-accent)}.fs-query{margin:10px 0 0;padding:8px 9px;border-left:2px solid var(--hv-color-accent);background:var(--hv-color-surface-muted);font-size:12px;font-weight:660}.fs-visual{display:grid;grid-template-columns:104px minmax(0,1fr);gap:9px;align-items:center;width:100%;margin-top:9px;border:1px solid var(--hv-color-border);border-radius:8px;padding:7px;background:var(--hv-color-surface);color:var(--hv-color-foreground);text-align:left;cursor:pointer}.fs-visual img{width:104px;height:96px;object-fit:contain;border-radius:5px;background:var(--hv-color-surface-muted)}.fs-visual strong,.fs-visual small{display:block}.fs-visual strong{margin-top:3px;font-size:12px}.fs-visual small{margin-top:3px;color:var(--hv-color-muted-foreground);font-size:9px}.fs-models{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px}.fs-model{border:1px solid var(--hv-color-border);border-radius:8px;padding:9px;background:var(--hv-color-surface)}.fs-model-top{display:flex;justify-content:space-between;gap:6px;font-weight:750}.fs-model-top span{display:flex;align-items:center;gap:5px}.fs-model-top i{width:7px;height:7px;border-radius:99px}.fs-model-top strong{font-size:17px}.fs-model>small{display:block;color:var(--hv-color-muted-foreground);font-size:8px}.fs-model p{margin:6px 0 0;color:var(--hv-color-muted-foreground);font-size:9px}.fs-cases{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px}.fs-case{border:1px solid var(--hv-color-border);border-radius:8px;padding:8px;background:var(--hv-color-surface);color:var(--hv-color-foreground);text-align:left;cursor:pointer}.fs-case:hover{border-color:color-mix(in srgb,var(--hv-color-accent) 55%,var(--hv-color-border))}.fs-case[aria-pressed=true]{border-color:var(--hv-color-accent);background:color-mix(in srgb,var(--hv-color-accent) 16%,var(--hv-color-surface));box-shadow:inset 0 0 0 1px var(--hv-color-accent)}.fs-case strong,.fs-case small{display:block}.fs-case small{margin-top:2px;color:var(--hv-color-muted-foreground);font-size:8px}.fs-benchmark{margin-top:13px;border-top:1px solid var(--hv-color-border);padding-top:10px}.fs-benchmark h3{margin:3px 0 2px;font-size:12px}.fs-caption{margin:0 0 7px;color:var(--hv-color-muted-foreground);font-size:9px}.fs-table{width:100%;border-collapse:collapse;font-size:9px}.fs-table th,.fs-table td{padding:5px 4px;border-bottom:1px solid var(--hv-color-border);text-align:right}.fs-table th:first-child,.fs-table td:first-child{text-align:left}.fs-table th{color:var(--hv-color-muted-foreground);font-size:8px;text-transform:uppercase}.fs-note{margin:7px 0 0;color:var(--hv-color-muted-foreground);font-size:9px}.fs-error{color:#ef4444}.fs-busy{opacity:.62}@media(max-width:390px){.fs-root{padding:10px}.fs-models{grid-template-columns:1fr}.fs-visual{grid-template-columns:82px minmax(0,1fr)}.fs-visual img{width:82px;height:78px}}
      `}</style>

      <header className="fs-header">
        <span className="fs-kicker">Catalog search</span>
        <h2>{mode === "photo" ? "Same product, another photo. Can search find it?" : `Does search find ${active.label.toLowerCase()}?`}</h2>
        <p>{mode === "photo" ? "Use one product photo to find its other catalog views." : "Compare the same detailed request across both models."}</p>
      </header>

      <nav className="fs-tabs" aria-label="Search type">
        <button type="button" className={`fs-tab${mode === "photo" ? " is-active" : ""}`} onClick={() => present(activePhoto, "photo")}>Photo match</button>
        <button type="button" className={`fs-tab${mode === "text" ? " is-active" : ""}`} onClick={() => present(activeText, "text")}>Typed search</button>
      </nav>

      {mode === "text" ? <blockquote className="fs-query">“{active.query}”</blockquote> : null}

      <button type="button" className="fs-visual" onClick={() => void setSelection([visualSampleId])}>
        {visualUrl ? <img src={visualUrl} alt={active.label} /> : null}
        <span><span className="fs-kicker">{mode === "photo" ? "Starting photo" : "Matching product"}</span><strong>{active.label}</strong><small>{mode === "photo" ? active.context : "Any view of this product counts as a match."}</small>{mode === "photo" ? <small>Correct means the same product ID, not a similar style.</small> : null}</span>
      </button>

      <section className="fs-models" aria-label="First matching product rank">
        <ModelCard name="Hyper3-CLIP" checkpoint={models.hyper3 || "v0.5"} color="#60a5fa" rank={active.target.hyper3Rank} readout={active.modelReadout.hyper3} />
        <ModelCard name="OpenAI CLIP" checkpoint={models.clip || "ViT-B/32"} color="#f59e0b" rank={active.target.clipRank} readout={active.modelReadout.clip} />
      </section>

      {mode === "photo" ? <nav className="fs-cases" aria-label="Photo matching examples">{photoCases.map((item) => <button key={item.id} type="button" className={`fs-case${busy ? " fs-busy" : ""}`} aria-pressed={item.id === active.id} disabled={busy} onClick={() => present(item, "photo")}><strong>{item.label}</strong><small>{item.context}</small></button>)}</nav> : textCases.length > 1 ? <nav className="fs-cases" aria-label="Typed search examples">{textCases.map((item) => <button key={item.id} type="button" className={`fs-case${busy ? " fs-busy" : ""}`} aria-pressed={item.id === active.id} disabled={busy} onClick={() => present(item, "text")}><strong>{item.label}</strong><small>{item.target.hyper3Rank === 1 ? "Hyper3 first" : item.target.clipRank === 1 ? "CLIP first" : "Compare ranks"}</small></button>)}</nav> : null}

      <section className="fs-benchmark" aria-label="Full benchmark results">
        <span className="fs-kicker">How the models compare</span>
        {mode === "photo" ? <>
          <h3>{photoBenchmark.queryCount} queries · {photoBenchmark.candidateCount} catalog photos</h3><p className="fs-caption">Correct means another view of the same product.</p>
          <table className="fs-table"><thead><tr><th>Correct product</th><th style={{color:"#60a5fa"}}>Hyper3</th><th style={{color:"#f59e0b"}}>CLIP</th></tr></thead><tbody><tr><td>Ranked first</td><td>{percentage(photoBenchmark.hyper3R1)}</td><td>{percentage(photoBenchmark.clipR1)}</td></tr><tr><td>Within top ten</td><td>{percentage(photoBenchmark.hyper3R10)}</td><td>{percentage(photoBenchmark.clipR10)}</td></tr><tr><td>Mean average precision</td><td>{Number(photoBenchmark.hyper3Map).toFixed(3)}</td><td>{Number(photoBenchmark.clipMap).toFixed(3)}</td></tr></tbody></table>
          <p className="fs-note">Cases use the largest first-match rank gap in each direction, so the CLIP win is shown too. Photo matching and typed retrieval are separate evaluations; their scores are not interchangeable.</p>
        </> : <>
          <h3>{typed.queryCount} written requests · {typed.candidateCount} photos</h3><p className="fs-caption">Correct means any view of the described product.</p>
          <table className="fs-table"><thead><tr><th>Correct product</th><th style={{color:"#60a5fa"}}>Hyper3</th><th style={{color:"#f59e0b"}}>CLIP</th></tr></thead><tbody><tr><td>Ranked first</td><td>{percentage(typed.hyper3Hit1)}</td><td>{percentage(typed.clipHit1)}</td></tr><tr><td>Within top ten</td><td>{percentage(typed.hyper3Hit10)}</td><td>{percentage(typed.clipHit10)}</td></tr><tr><td>Within top fifty</td><td>{percentage(typed.hyper3Hit50)}</td><td>{percentage(typed.clipHit50)}</td></tr></tbody></table>
          <p className="fs-note">This is one illustrative Hyper3 win. Across the full 1,120-photo benchmark, the models are close and OpenAI CLIP is ahead at fifty results. The visible workspace map contains {props.workspaceSampleCount || 741} catalog photos.</p>
        </>}
      </section>

      {samplePage.error ? <p className="fs-error">{samplePage.error}</p> : null}
      {error ? <p className="fs-error" role="alert">{error}</p> : null}
    </main>
  );
}
