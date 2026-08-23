const sdk = globalThis.HyperViewPanelSDK;
if (!sdk || sdk.version !== "2") {
  throw new Error("HyperViewPanelSDK v2 is required.");
}

const { React, hooks } = sdk;
const { usePanelActions, usePanelState, useSampleResults, useSamples, useSelection } = hooks;

function mediaUrl(sample) {
  const raw = sample?.media_url || sample?.thumbnail_url || sample?.thumbnail;
  return typeof raw === "string" && raw ? raw : null;
}

function percent(value) {
  return Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "—";
}

function BatchCard({ name, color, model }) {
  const noun = (count, singular, plural = `${singular}s`) => `${count} ${count === 1 ? singular : plural}`;
  return (
    <article className="vs-model">
      <div className="vs-model-head"><span><i style={{background:color}} />{name}</span></div>
      <div className="vs-counts">
        <span className="vs-exact">{noun(model.sameCategory, "exact label")}</span>
        <span className="vs-related">{noun(model.relatedCategory, "related label")}</span>
        <span className="vs-flagged">{noun(model.otherFlagged, "other flagged item")}</span>
        <span className="vs-manual">{noun(model.manualReview, "manual-review item")}</span>
      </div>
    </article>
  );
}

export default function SafetyComparisonPanel() {
  const { props = {}, state = {}, patchState } = usePanelState();
  const { updateProps } = usePanelActions();
  const { showResults } = useSampleResults();
  const { setSelection } = useSelection();
  const cases = Array.isArray(props.cases) ? props.cases : [];
  const activeCaseId = state.activeCaseId || props.initialCaseId || cases[0]?.id;
  const active = cases.find((item) => item.id === activeCaseId) || cases[0] || null;
  const clipPanelId = props.clipSamplesPanelId || "visual-safety-clip-queue";
  const samplePage = useSamples(props.collectionId, { pageSize: 200 });
  const sampleById = React.useMemo(() => new Map(samplePage.samples.map((sample) => [sample.id, sample])), [samplePage.samples]);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (samplePage.hasMore && !samplePage.loading) samplePage.loadMore();
  }, [samplePage.hasMore, samplePage.loading, samplePage.loadMore]);

  const chooseCase = (item) => {
    if (busy) return;
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        await showResults(item.models.hyper3.resultIds, {
          focus: false,
          source: `${item.label} review batch · Hyper3-CLIP`,
        });
        await updateProps(clipPanelId, { mode: "results", collectionId: item.models.clip.collectionId });
        await patchState({ activeCaseId: item.id });
        await setSelection([item.sampleId]);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : String(reason));
      } finally {
        setBusy(false);
      }
    })();
  };

  if (!active) return <main className="vs-root">No Visual Safety cases are available.</main>;

  const anchor = sampleById.get(active.sampleId);
  const anchorUrl = mediaUrl(anchor);
  const metrics = props.metrics || {};

  return (
    <main className="vs-root">
      <style>{`
        .vs-root,.vs-root *{box-sizing:border-box}.vs-root{height:100%;overflow:auto;padding:14px;color:var(--hv-color-foreground);background:var(--hv-color-background);font:11px/1.42 system-ui,-apple-system,BlinkMacSystemFont,sans-serif}.vs-kicker{display:block;color:var(--hv-color-muted-foreground);font-size:9px;font-weight:800;letter-spacing:.09em;text-transform:uppercase}.vs-header h2{margin:3px 0 0;font-size:18px;line-height:1.15;letter-spacing:-.02em}.vs-header p{margin:6px 0 0;color:var(--hv-color-muted-foreground)}.vs-anchor{display:grid;grid-template-columns:112px minmax(0,1fr);gap:10px;align-items:center;width:100%;margin-top:11px;border:1px solid var(--hv-color-border);border-radius:9px;padding:8px;background:var(--hv-color-surface);color:var(--hv-color-foreground);text-align:left;cursor:pointer}.vs-anchor img{width:112px;height:90px;object-fit:cover;border-radius:6px;background:var(--hv-color-surface-muted)}.vs-anchor strong,.vs-anchor small{display:block}.vs-anchor strong{margin-top:3px;font-size:13px}.vs-anchor small{margin-top:4px;color:var(--hv-color-muted-foreground);font-size:9px}.vs-models{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px}.vs-model{border:1px solid var(--hv-color-border);border-radius:8px;padding:9px;background:var(--hv-color-surface)}.vs-model-head{display:flex;align-items:center;justify-content:space-between;gap:6px;font-weight:750}.vs-model-head span{display:flex;align-items:center;gap:5px}.vs-model-head i{width:7px;height:7px;border-radius:99px}.vs-model-head strong{font-size:17px}.vs-model>small{display:block;color:var(--hv-color-muted-foreground);font-size:8px}.vs-counts{display:grid;gap:3px;margin-top:7px;color:var(--hv-color-muted-foreground);font-size:9px}.vs-counts b{color:var(--hv-color-foreground)}.vs-exact:before,.vs-related:before,.vs-flagged:before,.vs-manual:before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:5px}.vs-exact:before{background:#22c55e}.vs-related:before{background:#84cc16}.vs-flagged:before{background:#f59e0b}.vs-manual:before{background:#ef4444}.vs-legend{margin:8px 0 0;padding:7px 8px;border-left:2px solid var(--hv-color-accent);background:var(--hv-color-surface-muted);color:var(--hv-color-muted-foreground);font-size:9px}.vs-cases{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:10px}.vs-case{min-width:0;border:1px solid var(--hv-color-border);border-radius:7px;padding:7px;background:var(--hv-color-surface);color:var(--hv-color-foreground);text-align:left;cursor:pointer}.vs-case[aria-pressed=true]{border-color:var(--hv-color-accent);box-shadow:inset 0 0 0 1px var(--hv-color-accent)}.vs-case strong,.vs-case small{display:block}.vs-case small{margin-top:2px;color:var(--hv-color-muted-foreground);font-size:8px}.vs-benchmark{margin-top:13px;border-top:1px solid var(--hv-color-border);padding-top:10px}.vs-headline{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:8px 0 10px}.vs-headline>div{border:1px solid var(--hv-color-border);border-radius:8px;padding:9px;background:var(--hv-color-surface)}.vs-headline strong{display:block;margin-top:2px;font-size:22px;line-height:1.05;letter-spacing:-.02em}.vs-headline small{display:block;margin-top:3px;color:var(--hv-color-muted-foreground);font-size:9px}.vs-benchmark h3{margin:3px 0 2px;font-size:12px}.vs-caption{margin:0 0 7px;color:var(--hv-color-muted-foreground);font-size:9px}.vs-table{width:100%;border-collapse:collapse;font-size:9px}.vs-table th,.vs-table td{padding:5px 4px;border-bottom:1px solid var(--hv-color-border);text-align:right}.vs-table th:first-child,.vs-table td:first-child{text-align:left}.vs-table th{color:var(--hv-color-muted-foreground);font-size:8px;text-transform:uppercase}.vs-boundary{margin:8px 0 0;color:var(--hv-color-muted-foreground);font-size:9px}.vs-error{color:#ef4444}.vs-busy{opacity:.62}@media(max-width:390px){.vs-root{padding:10px}.vs-models{grid-template-columns:1fr}.vs-anchor{grid-template-columns:88px minmax(0,1fr)}.vs-anchor img{width:88px;height:74px}}
      `}</style>

      <header className="vs-header">
        <span className="vs-kicker">Review operations</span>
        <h2>One item was confirmed. What else belongs in the batch?</h2>
        <p>Compare the seven items a reviewer would inspect next.</p>
      </header>

      <button type="button" className="vs-anchor" onClick={() => void setSelection([active.sampleId])}>
        {anchorUrl ? <img src={anchorUrl} alt={active.sourceLabel} /> : null}
        <span><span className="vs-kicker">Confirmed item</span><strong>{active.sourceLabel}</strong><small>{active.context}</small></span>
      </button>

      <section className="vs-models" aria-label="Batch quality">
        <BatchCard name={props.models?.hyper3 || "Hyper3-CLIP"} color="#60a5fa" model={active.models.hyper3} />
        <BatchCard name={props.models?.clip || "OpenAI CLIP"} color="#f59e0b" model={active.models.clip} />
      </section>

      <p className="vs-legend">Exact and related labels stay within the confirmed item’s policy group. Other flagged items belong elsewhere; manual-review items may be noise.</p>

      <nav className="vs-cases" aria-label="Confirmed item examples">
        {cases.map((item) => <button key={item.id} type="button" className={`vs-case${busy ? " vs-busy" : ""}`} aria-pressed={item.id === active.id} disabled={busy} onClick={() => chooseCase(item)}><strong>{item.label}</strong><small>{item.context}</small></button>)}
      </nav>

      <section className="vs-benchmark" aria-label="Full batch benchmark">
        <span className="vs-kicker">What the queue misses</span>
        <h3>120 items · five-of-seven queue threshold</h3>
        <p className="vs-caption">A missed item ships harm to users; an extra queued item costs one human review. Review queues are tuned recall-first.</p>
        <div className="vs-headline">
          <div><span className="vs-kicker" style={{color:"#60a5fa"}}>Hyper3-CLIP</span><strong>{metrics.hyper3?.fn}</strong><small>of 60 harmful items missed · {percent(metrics.hyper3?.recall)} recall</small></div>
          <div><span className="vs-kicker" style={{color:"#f59e0b"}}>OpenAI CLIP</span><strong>{metrics.clip?.fn}</strong><small>of 60 harmful items missed · {percent(metrics.clip?.recall)} recall</small></div>
        </div>
        <p className="vs-caption">60 proxy-positive and 60 proxy-negative Open Images items. Full ledger, both directions:</p>
        <table className="vs-table"><thead><tr><th>Batch measure</th><th style={{color:"#60a5fa"}}>Hyper3</th><th style={{color:"#f59e0b"}}>CLIP</th></tr></thead><tbody>
          <tr><td>False negatives (missed)</td><td>{metrics.hyper3?.fn}</td><td>{metrics.clip?.fn}</td></tr>
          <tr><td>Queue recall</td><td>{percent(metrics.hyper3?.recall)}</td><td>{percent(metrics.clip?.recall)}</td></tr>
          <tr><td>Items queued</td><td>{metrics.hyper3?.queued}/120</td><td>{metrics.clip?.queued}/120</td></tr>
          <tr><td>False positives</td><td>{metrics.hyper3?.fp}</td><td>{metrics.clip?.fp}</td></tr>
          <tr><td>Queue precision</td><td>{percent(metrics.hyper3?.precision)}</td><td>{percent(metrics.clip?.precision)}</td></tr>
          <tr><td>AUROC (chance 50%)</td><td>{percent(metrics.hyper3?.auroc)}</td><td>{percent(metrics.clip?.auroc)}</td></tr>
        </tbody></table>
        <p className="vs-boundary">The same {metrics.hyper3?.threshold || "five-of-seven"} rule is used for both models. Open Images labels approximate review categories; the balanced 60/60 proxy split is not a production prevalence estimate. Small differences are descriptive, not proof of superiority.</p>
      </section>

      {samplePage.error ? <div className="vs-error">{samplePage.error}</div> : null}
      {error ? <div className="vs-error" role="alert">{error}</div> : null}
    </main>
  );
}
