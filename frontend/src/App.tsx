import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { SatelliteCanvas } from "./earlyWarning/SatelliteCanvas";
import { WeatherGlobe } from "./globe/WeatherGlobe";
import type { CycloneSummary, Forecast, Layers, TrackPoint } from "./types";

const DEFAULT_LAYERS: Layers = {
  wind: true,
  pressure: false,
  temperature: false,
  humidity: false,
  precipitation: false,
  sst: false,
  satellite: false,
  clouds: true,
  observed: true,
  aiTrack: true,
  ensemble: true,
  cone: true,
  landfall: true,
  historical: true,
  riskZones: true,
};

const MODELS = [
  { id: "indian_analog_ensemble", label: "Analog ensemble" },
  { id: "persistence", label: "Persistence" },
  { id: "climatology_steering", label: "NIO climatology" },
];

const TABS = ["Track", "Intensity", "Wind", "Pressure", "Uncertainty", "Notes"] as const;

export default function App() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const globeRef = useRef<WeatherGlobe | null>(null);
  const analyzeAbort = useRef<AbortController | null>(null);

  const [cyclones, setCyclones] = useState<CycloneSummary[]>([]);
  const [query, setQuery] = useState("");
  const [stormId, setStormId] = useState("");
  const [track, setTrack] = useState<TrackPoint[]>([]);
  const [timeIndex, setTimeIndex] = useState(8);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [layers, setLayers] = useState<Layers>(DEFAULT_LAYERS);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Track");
  const [model, setModel] = useState("indian_analog_ensemble");
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [weather, setWeather] = useState<any>(null);
  const [evalData, setEvalData] = useState<{ models?: Array<Record<string, unknown>> } | null>(null);
  const [compare, setCompare] = useState<Record<string, Forecast | null>>({});
  const [error, setError] = useState<string | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [trackLoading, setTrackLoading] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(true);
  const [workspace, setWorkspace] = useState<"replay" | "warning">("warning");
  const [imagery, setImagery] = useState("ir");
  const [region, setRegion] = useState("bob");
  const [analysis, setAnalysis] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [leadHours, setLeadHours] = useState(0);
  const [satPlaying, setSatPlaying] = useState(false);
  const [satFrame, setSatFrame] = useState(4);
  const [layersOpen, setLayersOpen] = useState(false);
  const [loadedId, setLoadedId] = useState("");

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const globe = new WeatherGlobe(canvas);
    globeRef.current = globe;
    const resize = () => {
      const host = canvas.parentElement;
      globe.resize(host?.clientWidth || window.innerWidth, host?.clientHeight || window.innerHeight);
    };
    resize();
    window.addEventListener("resize", resize);
    let raf = 0;
    const loop = () => {
      globe.tick();
      raf = requestAnimationFrame(loop);
    };
    loop();
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  useEffect(() => {
    const ac = new AbortController();
    (async () => {
      try {
        const [c, e] = await Promise.all([api.cyclones(ac.signal), api.evaluation(ac.signal)]);
        setCyclones(c.cyclones);
        setEvalData(e as { models?: Array<Record<string, unknown>> });
        const preferred =
          c.cyclones.find((x) => x.name === "AMPHAN") ||
          c.cyclones.find((x) => x.name === "TAUKTAE") ||
          c.cyclones.find((x) => x.name === "MOCHA") ||
          c.cyclones[0];
        if (preferred) setStormId(preferred.id);
      } catch (err) {
        if ((err as Error).name !== "AbortError") setError("Could not load the cyclone catalog.");
      } finally {
        setCatalogLoading(false);
      }
    })();
    return () => ac.abort();
  }, []);

  useEffect(() => {
    if (!stormId) return;
    const ac = new AbortController();
    setTrackLoading(true);
    setPlaying(false);
    setSatPlaying(false);
    setAnalysis(null);
    analyzeAbort.current?.abort();
    api
      .cyclone(stormId, ac.signal)
      .then((d) => {
        setTrack(d.track);
        setLoadedId(stormId);
        const idx = Math.min(Math.max(1, Math.floor(d.track.length * 0.4)), d.track.length - 1);
        setTimeIndex(idx);
        const p = d.track[idx];
        globeRef.current?.focusOn(p.lat, p.lon);
        setError(null);
      })
      .catch((err) => {
        if (err?.name !== "AbortError") setError("Could not load that cyclone track.");
      })
      .finally(() => setTrackLoading(false));
    return () => ac.abort();
  }, [stormId]);

  useEffect(() => {
    if (!stormId || !track.length) return;
    const ac = new AbortController();
    const t = window.setTimeout(() => {
      api.forecast(stormId, timeIndex, model, 11, ac.signal).then((f) => setForecast(f)).catch((err) => {
        if (err?.name !== "AbortError") setForecast(null);
      });
    }, 320);
    return () => {
      ac.abort();
      window.clearTimeout(t);
    };
  }, [stormId, timeIndex, model, track.length]);

  useEffect(() => {
    if (!stormId || !track.length) return;
    const ac = new AbortController();
    const t = window.setTimeout(() => {
      api.weather(stormId, timeIndex, ac.signal).then(setWeather).catch((err) => {
        if (err?.name !== "AbortError") setWeather(null);
      });
    }, 400);
    return () => {
      ac.abort();
      window.clearTimeout(t);
    };
  }, [stormId, timeIndex, track.length]);

  useEffect(() => {
    globeRef.current?.setEarlyWarning(
      analysis
        ? { points: analysis.forecast_points, activeLead: leadHours, riskZones: layers.riskZones }
        : null,
    );
    globeRef.current?.setStorm(track, forecast, timeIndex, layers, weather);
  }, [track, forecast, timeIndex, layers, weather, analysis, leadHours]);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setTimeIndex((i) => (!track.length ? i : i + 1 >= track.length ? 0 : i + 1));
    }, Math.round(1600 / speed));
    return () => window.clearInterval(id);
  }, [playing, speed, track.length]);

  const runAnalyze = async (immediate = false) => {
    if (!stormId || !track.length) return;
    analyzeAbort.current?.abort();
    const ac = new AbortController();
    analyzeAbort.current = ac;
    setAnalyzing(true);
    try {
      const a = await api.analyze(stormId, timeIndex, imagery, region, ac.signal);
      setAnalysis(a);
      if (immediate) {
        setLeadHours(0);
        setSatFrame(4);
      }
      setError(null);
    } catch (err) {
      if ((err as Error).name !== "AbortError") setError("Detection failed on this fix. Try again.");
    } finally {
      if (!ac.signal.aborted) setAnalyzing(false);
    }
  };

  useEffect(() => {
    if (workspace !== "warning" || !stormId || loadedId !== stormId || !track.length || playing) return;
    const t = window.setTimeout(() => {
      void runAnalyze(false);
    }, 750);
    return () => window.clearTimeout(t);
    // runAnalyze is recreated each render; deps below are the real triggers
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspace, stormId, loadedId, timeIndex, imagery, region, track.length, playing]);

  useEffect(() => {
    if (!satPlaying || !analysis?.satellite?.loop) return;
    const id = window.setInterval(() => {
      setSatFrame((f) => (f + 1) % 5);
    }, 900);
    return () => window.clearInterval(id);
  }, [satPlaying, analysis]);

  const filtered = useMemo(() => {
    const q = query.trim().toUpperCase();
    if (!q) return cyclones.slice(0, 80);
    return cyclones.filter((c) => c.name.includes(q) || String(c.season).includes(q) || c.id.includes(q)).slice(0, 80);
  }, [cyclones, query]);

  const here = track[Math.max(0, Math.min(timeIndex, Math.max(0, track.length - 1)))];
  const meta = cyclones.find((c) => c.id === stormId);
  const toggle = (k: keyof Layers) => setLayers((l) => ({ ...l, [k]: !l[k] }));

  const runCompare = async () => {
    if (!stormId) return;
    const entries = await Promise.all(MODELS.map(async (m) => [m.id, await api.forecast(stormId, timeIndex, m.id, 9)] as const));
    setCompare(Object.fromEntries(entries));
  };

  const satLoop = analysis?.satellite?.loop as Array<any> | undefined;
  const satNow = satLoop?.[satFrame]?.frame || analysis?.satellite?.frame || null;

  return (
    <div className="desk">
      <canvas ref={canvasRef} className="globe" />

      <header className="bar top">
        <div className="brand">
          <span className="mark" aria-hidden />
          <div>
            <strong>NIO cyclone desk</strong>
            <em>IBTrACS replay · Bay of Bengal / Arabian Sea</em>
          </div>
        </div>
        <div className="mode" role="tablist" aria-label="Workspace">
          <button type="button" className={workspace === "warning" ? "on" : ""} onClick={() => setWorkspace("warning")}>
            Early detection
          </button>
          <button type="button" className={workspace === "replay" ? "on" : ""} onClick={() => setWorkspace("replay")}>
            Replay
          </button>
        </div>
        <p className="notice">Not an IMD warning. Historical cases only.</p>
      </header>

      <button type="button" className="rail-toggle" onClick={() => setArchiveOpen((v) => !v)}>
        {archiveOpen ? "Hide cases" : "Cases"}
      </button>

      {archiveOpen && (
        <aside className="panel left">
          {workspace === "warning" && (
            <section className="sat-box">
              <h2>Satellite window</h2>
              <label className="field">
                Channel
                <select value={imagery} onChange={(e) => setImagery(e.target.value)}>
                  <option value="visible">Visible</option>
                  <option value="ir">Infrared</option>
                  <option value="wv">Water vapour</option>
                  <option value="eir">Enhanced IR</option>
                  <option value="ctt">Cloud-top temp</option>
                  <option value="multi">Multi-spectral</option>
                </select>
              </label>
              <label className="field">
                Basin
                <select value={region} onChange={(e) => setRegion(e.target.value)}>
                  <option value="bob">Bay of Bengal</option>
                  <option value="as">Arabian Sea</option>
                  <option value="nio">North Indian Ocean</option>
                  <option value="india">India &amp; coasts</option>
                </select>
              </label>
              <SatelliteCanvas imagery={imagery} frame={satNow} busy={analyzing && !satNow} />
              <div className="sat-actions">
                <button type="button" onClick={() => setSatPlaying((p) => !p)} disabled={!satLoop}>
                  {satPlaying ? "Pause frames" : "Loop T−12h"}
                </button>
                <button
                  type="button"
                  className="play"
                  onClick={() => void runAnalyze(true)}
                  disabled={analyzing || !stormId}
                >
                  {analyzing ? "Detecting…" : "Run detection"}
                </button>
              </div>
              <p className="fineprint">
                {satLoop ? `T−${satLoop[satFrame]?.hours_before_now ?? 0} h · ` : ""}
                Synthetic field around the best-track centre — not live INSAT.
              </p>
            </section>
          )}
          <label className="field">
            Case
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Amphan, Tauktae, 2021…" />
          </label>
          {catalogLoading && <p className="muted">Loading catalog…</p>}
          {trackLoading && <p className="muted">Loading track…</p>}
          {error && (
            <p className="err">
              {error}{" "}
              {workspace === "warning" && (
                <button type="button" className="inline" onClick={() => void runAnalyze(true)}>
                  Retry
                </button>
              )}
            </p>
          )}
          <div className="storms">
            {filtered.slice(0, workspace === "warning" ? 14 : 80).map((c) => (
              <button key={c.id} type="button" className={c.id === stormId ? "on" : ""} onClick={() => setStormId(c.id)}>
                <b>{titleCase(c.name)}</b>
                <span>
                  {c.season} · {c.genesis_basin === "BB" ? "Bay of Bengal" : "Arabian Sea"} ·{" "}
                  {c.peak_wind_kt ? `${Math.round(c.peak_wind_kt)} kt` : "wind missing"}
                </span>
              </button>
            ))}
          </div>
        </aside>
      )}

      <aside className="panel right">
        {workspace === "warning" ? (
          analysis ? (
            <>
              <p className="ew-kicker">{analysis.label}</p>
              <div className="ident">
                <h1>{titleCase(meta?.name || "System")}</h1>
                <p>{analysis.detection.system_label}</p>
              </div>
              <div className={`risk-meter lv${analysis.risk.level}`}>
                <b>
                  Risk {analysis.risk.level} / 5 — {analysis.risk.name}
                </b>
                <span>{analysis.risk.blurb}</span>
                <em>
                  Score {analysis.risk.score} · spread {analysis.risk.uncertainty} · detection{" "}
                  {pct(analysis.detection.cyclone_probability)}
                </em>
              </div>
              <dl>
                <div>
                  <dt>Centre</dt>
                  <dd>
                    {Number(analysis.detection.latitude).toFixed(1)}°N {Number(analysis.detection.longitude).toFixed(1)}°E
                  </dd>
                </div>
                <div>
                  <dt>Movement</dt>
                  <dd>
                    {analysis.movement.heading} · {Math.round(analysis.movement.speed_kmh)} km/h
                  </dd>
                </div>
                <div>
                  <dt>Max wind</dt>
                  <dd>{analysis.detection.max_wind_speed ?? "—"} kt</dd>
                </div>
                <div>
                  <dt>MSLP</dt>
                  <dd>{analysis.detection.central_pressure ?? "—"} hPa</dd>
                </div>
                <div>
                  <dt>Landfall</dt>
                  <dd>
                    {String(analysis.landfall.region ?? "n/a")} · {pct(analysis.landfall.probability)}
                  </dd>
                </div>
                <div>
                  <dt>Trend</dt>
                  <dd>{analysis.detection.trend}</dd>
                </div>
              </dl>
              <h2>What the field shows</h2>
              <p className="explain">{analysis.explanation}</p>
              <h2>Similar past storms</h2>
              <ul className="analogs">
                {(analysis.analogs || []).map((a: any) => (
                  <li key={a.id}>
                    <button type="button" onClick={() => setStormId(a.id)}>
                      <b>{titleCase(a.name)}</b> {a.season} · {a.peak_wind_kt ?? "—"} kt
                      {a.landfall ? ` · landfall ${Number(a.landfall.lat).toFixed(1)}°N` : ""}
                    </button>
                  </li>
                ))}
              </ul>
              <p className="fineprint">{analysis.disclaimer}</p>
            </>
          ) : (
            <div className="empty">
              <h1>{titleCase(meta?.name || "Pick a storm")}</h1>
              <p>
                {analyzing
                  ? "Running detection on this fix…"
                  : "Choose a historical cyclone, then Run detection. The scan uses the best-track centre at the time on the bar below."}
              </p>
            </div>
          )
        ) : (
          <>
            <div className="ident">
              <h1>{titleCase(meta?.name || "Select a storm")}</h1>
              <p>{here ? here.category : "—"}</p>
            </div>
            {here && (
              <dl>
                <div>
                  <dt>Centre</dt>
                  <dd>
                    {here.lat.toFixed(1)}°N {here.lon.toFixed(1)}°E
                  </dd>
                </div>
                <div>
                  <dt>Max wind</dt>
                  <dd>{here.wind_kt ?? "—"} kt</dd>
                </div>
                <div>
                  <dt>MSLP</dt>
                  <dd>{here.pres_hpa ?? "—"} hPa</dd>
                </div>
                <div>
                  <dt>Motion</dt>
                  <dd>
                    {forecast?.now.heading ?? "—"} {forecast?.now.speed_kt ?? here.speed_kt ?? "—"} kt
                  </dd>
                </div>
                <div>
                  <dt>Genesis climo</dt>
                  <dd>
                    {pct(forecast?.formation.window_hours["24"])} / {pct(forecast?.formation.window_hours["48"])} /{" "}
                    {pct(forecast?.formation.window_hours["72"])}
                  </dd>
                </div>
                <div>
                  <dt>RI probability</dt>
                  <dd>{pct(forecast?.rapid_intensification_probability)}</dd>
                </div>
              </dl>
            )}
            <p className="fineprint">{forecast?.disclaimer}</p>
          </>
        )}

        <nav className="tabs">
          {TABS.map((t) => (
            <button key={t} type="button" className={tab === t ? "on" : ""} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </nav>
        <div className="tab-body">{renderTab(tab, forecast)}</div>

        <button type="button" className="ghost" onClick={() => setLayersOpen((v) => !v)}>
          {layersOpen ? "Hide map layers" : "Map layers"}
        </button>
        {layersOpen && (
          <>
            <h2>Atmosphere</h2>
            <div className="chips">
              {(
                [
                  ["wind", "Wind"],
                  ["pressure", "Pressure"],
                  ["temperature", "Temp"],
                  ["humidity", "Humidity"],
                  ["precipitation", "Rain"],
                  ["sst", "SST"],
                  ["clouds", "Clouds"],
                  ["satellite", "IR proxy"],
                ] as const
              ).map(([k, lab]) => (
                <button key={k} type="button" className={layers[k] ? "chip on" : "chip"} onClick={() => toggle(k)}>
                  {lab}
                </button>
              ))}
            </div>
            <h2>Tracks</h2>
            <div className="chips">
              {(
                [
                  ["observed", "Observed"],
                  ["aiTrack", "Mean forecast"],
                  ["ensemble", "Ensemble"],
                  ["cone", "Cone"],
                  ["landfall", "Landfall"],
                  ["historical", "History"],
                  ["riskZones", "Risk"],
                ] as const
              ).map(([k, lab]) => (
                <button key={k} type="button" className={layers[k] ? "chip on" : "chip"} onClick={() => toggle(k)}>
                  {lab}
                </button>
              ))}
            </div>
          </>
        )}

        <h2>Guidance</h2>
        <select value={model} onChange={(e) => setModel(e.target.value)}>
          {MODELS.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </select>
        <button type="button" className="ghost" onClick={() => void runCompare()}>
          Compare models at this fix
        </button>
        {evalData?.models && (
          <div className="eval">
            {(evalData.models as Array<any>).map((m) => (
              <p key={m.model}>
                <b>{m.model}</b> 24h {m.track_error_km?.["24"]?.mean ?? "—"} km · 72h {m.track_error_km?.["72"]?.mean ?? "—"} km
              </p>
            ))}
          </div>
        )}
        {Object.keys(compare).length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Model</th>
                <th>+24 h</th>
                <th>+72 h</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(compare).map(([id, f]) => (
                <tr key={id}>
                  <td>{id.replaceAll("_", " ")}</td>
                  <td>{fmtErr(f?.verification?.errors?.["24"])}</td>
                  <td>{fmtErr(f?.verification?.errors?.["72"])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </aside>

      <div className="legend">
        <i className="g" /> Observed
        <i className="c" /> Forecast
        <i className="b" /> Ensemble
        <i className="o" /> Cone
      </div>

      {workspace === "warning" && analysis && (
        <div className="ew-leads">
          {[0, 6, 12, 24, 48, 72, 96, 120].map((h) => (
            <button key={h} type="button" className={leadHours === h ? "on" : ""} onClick={() => setLeadHours(h)}>
              {h === 0 ? "Now" : `+${h}h`}
            </button>
          ))}
        </div>
      )}

      <footer className="bar bottom">
        <button type="button" onClick={() => setTimeIndex((i) => Math.max(0, i - 1))} disabled={!track.length}>
          Back
        </button>
        <button type="button" className="play" onClick={() => setPlaying((p) => !p)} disabled={!track.length}>
          {playing ? "Pause" : "Play"}
        </button>
        <button type="button" onClick={() => setTimeIndex((i) => Math.min(track.length - 1, i + 1))} disabled={!track.length}>
          Fwd
        </button>
        <label>
          {speed.toFixed(1)}×
          <input type="range" min={0.5} max={4} step={0.5} value={speed} onChange={(e) => setSpeed(Number(e.target.value))} />
        </label>
        <input
          className="scrub"
          type="range"
          min={0}
          max={Math.max(0, track.length - 1)}
          value={timeIndex}
          onChange={(e) => setTimeIndex(Number(e.target.value))}
        />
        <time>{here?.iso_time?.replace(" ", " · ") || "—"} UTC</time>
      </footer>
    </div>
  );
}

function renderTab(tab: string, forecast: Forecast | null) {
  if (!forecast) return <p className="muted">No forecast for this time yet.</p>;
  if (tab === "Track") {
    return (
      <table>
        <thead>
          <tr>
            <th>Lead</th>
            <th>Lat</th>
            <th>Lon</th>
            <th>Error</th>
          </tr>
        </thead>
        <tbody>
          {forecast.mean_track.map((p) => (
            <tr key={p.lead_hours}>
              <td>{p.lead_hours ? `+${p.lead_hours}h` : "Now"}</td>
              <td>{p.lat.toFixed(1)}</td>
              <td>{p.lon.toFixed(1)}</td>
              <td>{fmtErr(forecast.verification?.errors?.[String(p.lead_hours)])}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  if (tab === "Intensity" || tab === "Wind") {
    return (
      <table>
        <thead>
          <tr>
            <th>Lead</th>
            <th>Wind</th>
            <th>Category</th>
          </tr>
        </thead>
        <tbody>
          {forecast.mean_track.map((p) => (
            <tr key={p.lead_hours}>
              <td>{p.lead_hours ? `+${p.lead_hours}h` : "Now"}</td>
              <td>{p.wind_kt} kt</td>
              <td>{p.category}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  if (tab === "Pressure") {
    return (
      <table>
        <thead>
          <tr>
            <th>Lead</th>
            <th>MSLP</th>
          </tr>
        </thead>
        <tbody>
          {forecast.mean_track.map((p) => (
            <tr key={p.lead_hours}>
              <td>{p.lead_hours ? `+${p.lead_hours}h` : "Now"}</td>
              <td>{p.pres_hpa} hPa</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  if (tab === "Uncertainty") {
    return (
      <p>
        Ensemble spread at +72 h is {forecast.mean_track.find((p) => p.lead_hours === 72)?.spread_km ?? "—"} km. Landfall
        chance {pct(forecast.landfall?.probability as number | undefined)} near {String(forecast.landfall?.region ?? "n/a")}.
      </p>
    );
  }
  return <p>INSAT granules are not in this build. The IR window is a parametric field around the best-track centre.</p>;
}

function titleCase(name: string) {
  if (!name || name === "UNNAMED") return "Unnamed system";
  return name.charAt(0) + name.slice(1).toLowerCase();
}
function pct(v?: number) {
  if (v == null || Number.isNaN(v)) return "—";
  return `${Math.round(v * 100)}%`;
}
function fmtErr(v?: number | null) {
  if (v == null) return "—";
  return `${v} km`;
}
