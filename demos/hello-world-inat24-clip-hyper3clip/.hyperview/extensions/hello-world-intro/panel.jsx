const sdk = globalThis.HyperViewPanelSDK;
if (!sdk || sdk.version !== "2") {
  throw new Error("HyperViewPanelSDK v2 is not available on window.");
}

const { React, components = {}, hooks = {} } = sdk;
const Panel = components.Panel || (({ children, className = "" }) => (
  <div className={`flex flex-col h-full bg-card overflow-hidden ${className}`.trim()} style={{ height: "100%" }}>
    {children}
  </div>
));
const { usePanelState, useSelection } = hooks;

const geometryColors = {
  Euclidean: "#67e8f9",
  Spherical: "#a78bfa",
  "Hyperbolic · Poincare": "#fb923c",
};

export default function HelloWorldIntro() {
  const { props } = usePanelState();
  const { selectedIds } = useSelection();
  const geometries = Array.isArray(props.geometries) ? props.geometries : [];

  return (
    <Panel>
      <div className="hello-world-intro">
        <span className="hello-world-kicker">HyperView Hello World</span>
        <h2>One image collection.<br />Three geometries.</h2>
        <p className="hello-world-lede">
          Every map contains the same {props.sampleCount || 300} {props.dataset || "iNaturalist"} observations.
          What changes is the representation and the geometry used to lay it out.
        </p>

        <div className="hello-world-geometry-list">
          {geometries.map((geometry) => (
            <article key={geometry.name}>
              <i style={{ background: geometryColors[geometry.name] || "#94a3b8" }} />
              <span>
                <strong>{geometry.name}</strong>
                <small>{geometry.model} · {geometry.dimension}</small>
              </span>
            </article>
          ))}
        </div>

        <div className="hello-world-steps">
          <strong>Try this</strong>
          <ol>
            <li>Rotate and zoom each map.</li>
            <li>Select a cluster in one view.</li>
            <li>Compare where that selection lands in the other geometries.</li>
            <li>Open Samples to inspect the underlying observations.</li>
          </ol>
        </div>

        <div className={`hello-world-selection${selectedIds.length ? " is-active" : ""}`}>
          <span>{selectedIds.length ? selectedIds.length : "No"}</span>
          {selectedIds.length === 1 ? " observation selected" : " observations selected"}
        </div>
      </div>

      <style>{`
        .hello-world-intro { height: 100%; overflow: auto; padding: 22px; color: var(--hv-color-foreground); background: radial-gradient(circle at 90% 0%, color-mix(in srgb, var(--hv-color-accent) 12%, transparent), transparent 32%); }
        .hello-world-kicker { color: var(--hv-color-accent); font: 600 10px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .16em; text-transform: uppercase; }
        .hello-world-intro h2 { margin: 12px 0 10px; font: 650 27px/1.08 system-ui, sans-serif; letter-spacing: -.035em; }
        .hello-world-lede { margin: 0; color: var(--hv-color-muted-foreground); font: 13px/1.55 system-ui, sans-serif; }
        .hello-world-geometry-list { display: grid; gap: 8px; margin: 20px 0; }
        .hello-world-geometry-list article { display: flex; align-items: center; gap: 11px; padding: 11px 12px; border: 1px solid var(--hv-color-border); border-radius: 10px; background: color-mix(in srgb, var(--hv-color-surface) 86%, transparent); }
        .hello-world-geometry-list i { width: 8px; height: 30px; border-radius: 999px; }
        .hello-world-geometry-list span { display: grid; gap: 2px; }
        .hello-world-geometry-list strong { font: 600 12px/1.2 system-ui, sans-serif; }
        .hello-world-geometry-list small { color: var(--hv-color-muted-foreground); font: 10px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; }
        .hello-world-steps { padding: 14px; border: 1px solid var(--hv-color-border); border-radius: 12px; background: var(--hv-color-surface-muted); font: 12px/1.5 system-ui, sans-serif; }
        .hello-world-steps > strong { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }
        .hello-world-steps ol { margin: 9px 0 0; padding-left: 19px; color: var(--hv-color-muted-foreground); }
        .hello-world-steps li + li { margin-top: 5px; }
        .hello-world-selection { display: flex; align-items: baseline; gap: 6px; margin-top: 14px; color: var(--hv-color-muted-foreground); font: 11px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace; }
        .hello-world-selection span { color: var(--hv-color-foreground); font-size: 18px; font-weight: 650; }
        .hello-world-selection.is-active span { color: var(--hv-color-accent); }
      `}</style>
    </Panel>
  );
}
