const sdk = globalThis.HyperViewPanelSDK;
if (!sdk || sdk.version !== "2") {
  throw new Error("HyperViewPanelSDK v2 is not available on window.");
}

const { React, components, hooks } = sdk;
const { Panel } = components;
const {
  usePanelActions,
  usePanelState,
  useSampleResults,
  useSamples,
  useSelection,
} = hooks;

function mediaUrl(sample) {
  const raw = sample?.media_url || sample?.thumbnail_url || sample?.thumbnail;
  return typeof raw === "string" && raw ? raw : null;
}

function modelColor(modelKey) {
  return modelKey === "candidate" ? "#60a5fa" : "#f59e0b";
}

function modelName(models, modelKey) {
  return models.find((model) => model.key === modelKey)?.displayName || modelKey;
}

function SectionButton({ active, children, onClick }) {
  return (
    <button type="button" className={`abo-section-button${active ? " is-active" : ""}`} onClick={onClick}>
      {children}
    </button>
  );
}

function ImageCaseButton({ item, sample, models, active, busy, onClick }) {
  const src = mediaUrl(sample);
  return (
    <button
      type="button"
      className={`abo-case abo-image-case${active ? " is-active" : ""}`}
      aria-pressed={active}
      disabled={busy}
      onClick={onClick}
    >
      {src ? <img src={src} alt="" loading="lazy" /> : <span className="abo-image-placeholder" />}
      <span className="abo-case-body">
        <span className="abo-case-head">
          <strong>{item.title}</strong>
          <ScoreBadges
            item={item}
            models={models}
            render={(s) => (s.hits == null ? "—" : `${s.hits}/10`)}
          />
        </span>
        <small>{item.family}</small>
      </span>
    </button>
  );
}

function TextCaseButton({ item, models, active, busy, onClick }) {
  return (
    <button
      type="button"
      className={`abo-case abo-text-case${active ? " is-active" : ""}`}
      aria-pressed={active}
      disabled={busy}
      onClick={onClick}
    >
      <span className="abo-case-head">
        <strong>{item.title}</strong>
        <ScoreBadges item={item} models={models} render={(s) => (s.rank ? `#${s.rank}` : "—")} />
      </span>
      <small>{item.family}</small>
    </button>
  );
}

// The result belongs on the menu, not two clicks in: a viewer should see which
// model wins each case before choosing one.
function ScoreBadges({ item, models, render }) {
  return (
    <span className="abo-scores">
      {["candidate", "clip"].map((modelKey) => {
        const summary = item.summaries?.[modelKey] || {};
        const label = render(summary);
        if (label === "—") return null;
        return (
          <span key={modelKey} className="abo-score" style={{ color: modelColor(modelKey) }}>
            <i style={{ background: modelColor(modelKey) }} />
            {modelName(models, modelKey)} {label}
          </span>
        );
      })}
    </span>
  );
}

function ImageEvidence({ item, models }) {
  return (
    <>
      <div className="abo-question-block">
        <span className="abo-kicker">Active catalog question</span>
        <h3>{item.title}</h3>
        <p>{item.guide}</p>
      </div>
      <div className="abo-model-grid">
        {["candidate", "clip"].map((modelKey) => {
          const summary = item.summaries?.[modelKey] || {};
          return (
            <article className="abo-model-card" key={modelKey}>
              <div className="abo-model-row">
                <span><i style={{ background: modelColor(modelKey) }} />{modelName(models, modelKey)}</span>
                <strong style={{ color: modelColor(modelKey) }}>
                  {Number.isFinite(summary.hits) ? `${summary.hits}/10` : "—"}
                </strong>
              </div>
              <small>neighbours in the expected family</small>
              <p>{summary.text}</p>
            </article>
          );
        })}
      </div>
    </>
  );
}

function TextEvidence({ item, models, samplesById, onShowResults, onTarget }) {
  const target = samplesById.get(item.targetSampleId);
  const targetSrc = mediaUrl(target);
  return (
    <>
      <div className="abo-query-card">
        <span className="abo-kicker">Catalog attribute query</span>
        <blockquote>“{item.query}”</blockquote>
      </div>

      <button type="button" className="abo-target" onClick={onTarget}>
        {targetSrc ? <img src={targetSrc} alt="" /> : <span className="abo-image-placeholder" />}
        <span>
          <small>Exact catalog target</small>
          <strong>{item.targetTitle}</strong>
        </span>
      </button>

      <div className="abo-model-grid">
        {["candidate", "clip"].map((modelKey) => {
          const summary = item.summaries?.[modelKey] || {};
          const model = models.find((entry) => entry.key === modelKey);
          const rows = item.results?.[modelKey] || [];
          // A shortlist of six plausible products looks the same whether or not
          // it contains the one the shopper asked for. Say which it is.
          const targetInTop = rows.some(
            (row) => row.target || row.id === item.targetSampleId,
          );
          return (
            <article
              key={modelKey}
              className="abo-model-card"
            >
              <span className="abo-model-row">
                <span><i style={{ background: modelColor(modelKey) }} />{modelName(models, modelKey)}</span>
                <strong style={{ color: modelColor(modelKey) }}>#{summary.rank ?? "—"}</strong>
              </span>
              <small>exact target rank · shortlist shown {modelKey === "candidate" ? "left" : "right"}</small>
              <span className={`abo-visibility${targetInTop ? " is-hit" : " is-miss"}`}>
                {targetInTop ? "target visible in top 6" : "target not visible in top 6"}
              </span>
              <p>{summary.text}</p>
              <span className="abo-mini-actions">
                <button type="button" className="abo-mini" onClick={() => onShowResults(model)}>
                  show top 6
                </button>
                <button
                  type="button"
                  className="abo-mini"
                  onClick={() => onTarget(model)}
                  title="Select the exact target and focus this model's map"
                >
                  target
                </button>
              </span>
            </article>
          );
        })}
      </div>
    </>
  );
}

export default function CatalogRetrievalPanel() {
  const { props = {}, state = {}, patchState } = usePanelState();
  const { focusPanel, updateProps } = usePanelActions();
  const { setSelection } = useSelection();
  const { resetResults } = useSampleResults();
  const examples = Array.isArray(props.examples) ? props.examples : [];
  const models = Array.isArray(props.models) ? props.models : [];
  const imageExamples = examples.filter((item) => item.mode === "image-neighborhood");
  const textExamples = examples.filter((item) => item.mode === "text-to-product");
  const activeSection = state.activeSection === "text" ? "text" : "image";
  const activeImage = imageExamples.find((item) => item.id === state.activeImageCaseId) || imageExamples[0];
  const activeText = textExamples.find((item) => item.id === state.activeTextCaseId) || textExamples[0];
  const samplePage = useSamples(props.collectionId, { pageSize: 500 });
  const samplesById = React.useMemo(
    () => new Map(samplePage.samples.map((sample) => [sample.id, sample])),
    [samplePage.samples],
  );
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (samplePage.hasMore && !samplePage.loading) samplePage.loadMore();
  }, [samplePage.hasMore, samplePage.loading, samplePage.loadMore]);

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

  const chooseImage = (item) => void run(async () => {
    for (const model of models) {
      await updateProps(model.rankPanelId, {
        mode: "ranked",
        labelField: "title",
        rank: {
          anchorSampleId: item.queryId,
          layoutKey: model.layoutKey,
          k: 10,
          source: `${model.displayName || model.key} image neighbours`,
          showDistance: false,
        },
      });
    }
    await patchState({ activeSection: "image", activeImageCaseId: item.id });
    await setSelection([item.queryId]);
    const primaryRankPanel = models.find((model) => model.key === "candidate")?.rankPanelId;
    if (primaryRankPanel) await focusPanel(primaryRankPanel);
  });

  const chooseText = (item) => void run(async () => {
    for (const model of models) {
      const collectionId = item.collectionIds?.[model.key];
      if (!collectionId) throw new Error(`No ${model.displayName || model.key} shortlist is available.`);
      await updateProps(model.rankPanelId, { mode: "results", collectionId, labelField: "title" });
    }
    await patchState({
      activeSection: "text",
      activeTextCaseId: item.id,
    });
    await setSelection([item.targetSampleId]);
    const primaryRankPanel = models.find((model) => model.key === "candidate")?.rankPanelId;
    if (primaryRankPanel) await focusPanel(primaryRankPanel);
  });

  // Ported from the pre-1.0 walkthrough. Reading "#20" asks the viewer to take
  // the miss on faith; these let them go and look at it.
  const showResults = (item, model) => void run(async () => {
    const ids = (item.results?.[model?.key] || []).map((row) => row.id).filter(Boolean);
    if (!ids.length) throw new Error("No shortlist is available for this model.");
    await setSelection(ids);
    if (model?.rankPanelId) await focusPanel(model.rankPanelId);
  });

  const showTarget = (item, model) => void run(async () => {
    if (!item.targetSampleId) throw new Error("This case has no exact target.");
    await setSelection([item.targetSampleId]);
    if (model?.mapPanelId) await focusPanel(model.mapPanelId);
  });

  const reset = () => {
    const item = imageExamples.find((entry) => entry.id === props.initialImageCaseId) || imageExamples[0];
    if (item) chooseImage(item);
  };

  return (
    <Panel>
      <div className="abo-root">
        <style>{`
          .abo-root{box-sizing:border-box;flex:1;min-height:0;overflow:auto;padding:14px;background:var(--hv-color-background);color:var(--hv-color-foreground);font:12px/1.45 system-ui,-apple-system,BlinkMacSystemFont,sans-serif}
          .abo-root *{box-sizing:border-box}.abo-header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.abo-kicker,.abo-case-kicker{display:block;color:var(--hv-color-muted-foreground);font-size:9px;font-weight:800;letter-spacing:.09em;text-transform:uppercase}.abo-header h2{margin:3px 0 0;font-size:18px;line-height:1.12;letter-spacing:-.02em}.abo-header p{margin:7px 0 0;color:var(--hv-color-muted-foreground)}
          .abo-reset,.abo-action{border:1px solid var(--hv-color-border);border-radius:6px;padding:6px 9px;background:var(--hv-color-surface-muted);color:var(--hv-color-foreground);cursor:pointer;font-size:11px}.abo-sections{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin:13px 0 10px}.abo-section-button{border:1px solid var(--hv-color-border);border-radius:7px;padding:8px;background:var(--hv-color-surface);color:var(--hv-color-muted-foreground);cursor:pointer;font-weight:700}.abo-section-button.is-active{border-color:var(--hv-color-accent);background:color-mix(in srgb,var(--hv-color-accent) 16%,var(--hv-color-surface));color:var(--hv-color-foreground)}
          .abo-cases{display:grid;gap:6px}.abo-case{display:flex;min-width:0;align-items:center;gap:8px;border:1px solid var(--hv-color-border);border-radius:7px;padding:7px;background:var(--hv-color-surface);color:var(--hv-color-foreground);text-align:left;cursor:pointer}.abo-case.is-active{border-color:var(--hv-color-accent);box-shadow:inset 0 0 0 1px var(--hv-color-accent)}.abo-case img,.abo-image-placeholder{width:40px;height:40px;flex:0 0 40px;border-radius:5px;object-fit:contain;background:var(--hv-color-surface-muted)}.abo-case strong,.abo-case small{display:block}.abo-case small{margin-top:2px;color:var(--hv-color-muted-foreground);font-size:9px}.abo-text-case{display:block}.abo-case-kicker{margin-bottom:3px}
          .abo-question-block,.abo-query-card{margin-top:10px;border-top:1px solid var(--hv-color-border);padding-top:10px}.abo-question-block h3{margin:3px 0;font-size:14px}.abo-question-block p,.abo-hint{margin:5px 0 0;color:var(--hv-color-muted-foreground)}.abo-query-card blockquote{margin:6px 0 0;font-size:13px;font-weight:650;line-height:1.45}.abo-target{display:flex;width:100%;align-items:center;gap:9px;margin-top:9px;border:1px solid var(--hv-color-accent);border-radius:8px;padding:8px;background:var(--hv-color-surface);color:var(--hv-color-foreground);text-align:left;cursor:pointer}.abo-target img,.abo-target .abo-image-placeholder{width:62px;height:62px;flex:0 0 62px;object-fit:contain;border-radius:6px;background:var(--hv-color-surface-muted)}.abo-target small,.abo-target strong{display:block}.abo-target small{color:var(--hv-color-muted-foreground);font-size:9px;text-transform:uppercase;letter-spacing:.07em}.abo-target strong{margin-top:4px;font-size:11px}
          .abo-case-body{min-width:0}.abo-case-head{display:flex;align-items:baseline;justify-content:space-between;gap:8px;min-width:0}.abo-scores{display:flex;gap:7px;flex:0 0 auto;font-size:9px;font-weight:800;white-space:nowrap}.abo-score{display:flex;align-items:center;gap:3px}.abo-score i{width:5px;height:5px;border-radius:99px;flex:0 0 auto}.abo-visibility{display:block;margin-top:5px;font-size:9px;font-weight:800;letter-spacing:.04em}.abo-visibility.is-hit{color:#22c55e}.abo-visibility.is-miss{color:#f59e0b}.abo-mini-actions{display:flex;gap:5px;margin-top:7px}.abo-mini{border:1px solid var(--hv-color-border);border-radius:5px;padding:3px 7px;background:var(--hv-color-surface-muted);color:var(--hv-color-foreground);cursor:pointer;font-size:9px;font-weight:700}.abo-mini:hover{border-color:var(--hv-color-accent)}.abo-model-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px}.abo-model-card{border:1px solid var(--hv-color-border);border-radius:8px;padding:9px;background:var(--hv-color-surface);color:var(--hv-color-foreground);text-align:left}.abo-model-row{display:flex;align-items:center;justify-content:space-between;gap:6px;font-weight:750}.abo-model-row span{display:flex;align-items:center;gap:5px;min-width:0}.abo-model-row i{width:7px;height:7px;border-radius:99px;flex:0 0 auto}.abo-model-row strong{font-size:14px}.abo-model-card small{display:block;margin-top:3px;color:var(--hv-color-muted-foreground);font-size:9px}.abo-model-card p{margin:6px 0 0;color:var(--hv-color-muted-foreground);font-size:10px;line-height:1.4}.abo-actions{display:flex;gap:6px;margin-top:10px}.abo-error{color:#ef4444}
          @media(max-width:420px){.abo-root{padding:10px}.abo-model-grid{grid-template-columns:1fr}}
        `}</style>

        <header className="abo-header">
          <div>
            <span className="abo-kicker">ABO retrieval workbench</span>
            <h2>Does the model find the right product?</h2>
            <p>Search from a product photo or a detailed shopper request.</p>
          </div>
          <button type="button" className="abo-reset" disabled={busy} onClick={reset}>Reset</button>
        </header>

        <nav className="abo-sections" aria-label="Retrieval mode">
          <SectionButton active={activeSection === "text"} onClick={() => activeText && chooseText(activeText)}>
            Text → product
          </SectionButton>
          <SectionButton active={activeSection === "image"} onClick={() => activeImage && chooseImage(activeImage)}>
            Image → neighbours
          </SectionButton>
        </nav>

        {activeSection === "image" ? (
          <>
            <div className="abo-cases">
              {imageExamples.map((item) => (
                <ImageCaseButton
                  key={item.id}
                  item={item}
                  sample={samplesById.get(item.queryId)}
                  models={models}
                  active={item.id === activeImage?.id}
                  busy={busy}
                  onClick={() => chooseImage(item)}
                />
              ))}
            </div>
            {activeImage ? <ImageEvidence item={activeImage} models={models} /> : null}
          </>
        ) : (
          <>
            <div className="abo-cases">
              {textExamples.map((item) => (
                <TextCaseButton
                  key={item.id}
                  item={item}
                  models={models}
                  active={item.id === activeText?.id}
                  busy={busy}
                  onClick={() => chooseText(item)}
                />
              ))}
            </div>
            {activeText ? (
              <TextEvidence
                item={activeText}
                models={models}
                samplesById={samplesById}
                onShowResults={(model) => showResults(activeText, model)}
                onTarget={(model) => showTarget(activeText, model)}
              />
            ) : null}
            <div className="abo-actions">
              <button type="button" className="abo-action" disabled={busy} onClick={() => void run(async () => {
                await resetResults({ focus: false, source: "catalog-browse" });
                await focusPanel(props.samplesPanelId || "samples");
              })}>
                Browse all {samplePage.total.toLocaleString()} products
              </button>
            </div>
          </>
        )}

        {samplePage.loading ? <p className="abo-hint">Loading catalog records…</p> : null}
        {samplePage.error ? <p className="abo-error">{samplePage.error}</p> : null}
        {error ? <p className="abo-error">{error}</p> : null}

      </div>
    </Panel>
  );
}
