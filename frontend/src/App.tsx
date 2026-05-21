import { useCallback, useEffect, useRef, useState } from 'react';
import { motion, useMotionValue, useSpring } from 'framer-motion';
import EntranceExperience from './components/EntranceExperience';
import BrainAtlas from './components/BrainAtlas';
import ManualPortfolio from './components/ManualPortfolio';
import RealisticHollowBrain from './components/RealisticHollowBrain';
import MarketCandlestickChart from './components/MarketCandlestickChart';
import { useAuth } from './context/AuthContext';
import { AuthScreen } from './components/AuthScreen';
import { AccessCodeScreen } from './components/AccessCodeScreen';
import { AdminPanel } from './components/AdminPanel';
import {
  deleteNumerisInteraction,
  getGeopoliticalNews,
  getNumerisDashboard,
  sendNumerisPrompt,
  tuneNumerisSimulation,
  type GeoNewsItem,
  type NumerisData,
} from './lib/api';
import {
  ArrowUpRight,
  BrainCircuit,
  Command,
  ExternalLink,
  Globe2,
  Layers3,
  Mic2,
  Network,
  Newspaper,
  Radar,
  RadioTower,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  TrendingUp,
  Waves,
} from 'lucide-react';

type Module = {
  id: number;
  name: string;
  domain: string;
  description: string;
  status: string;
  metric: number;
  gradient: string;
  depth: number;
};

type Signal = {
  id: number;
  symbol: string;
  verdict: string;
  confidence: number;
  momentum: number;
  risk: number;
  agent: string;
  price: number;
};

type Simulation = {
  id: number;
  name: string;
  engine: string;
  region: string;
  intensity: number;
  forecast: string;
  updated_at: string;
};

type Report = {
  id: number;
  title: string;
  category: string;
  severity: string;
  summary: string;
  created_at: string;
};

type Interaction = {
  id: number;
  prompt: string;
  response: string;
  agent: string;
  confidence: number;
  created_at: string;
};

type EventStreamItem = {
  id: number;
  event_type: string;
  title: string;
  detail: string;
  impact: number;
  region: string;
  created_at: string;
};

const initialData: NumerisData = {
  modules: [],
  signals: [],
  simulations: [],
  reports: [],
  interactions: [],
  events: [],
  brainTraits: [],
  brainRegions: [],
};

function ScrollProgress() {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let ticking = false;
    const update = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
      const scrollable = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(scrollable <= 0 ? 0 : (window.scrollY / scrollable) * 100);
        ticking = false;
      });
    };
    update();
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
    };
  }, []);

  return <div className="scroll-progress"><span style={{ width: `${progress}%` }} /></div>;
}

function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion) return;
    let frame = 0;
    let animation = 0;
    let lastDraw = 0;
    const isSmallScreen = window.innerWidth < 760;
    const particleCount = isSmallScreen ? 42 : 68;
    const particles = Array.from({ length: particleCount }, (_, index) => ({
      seed: index * 41,
      radius: 0.7 + (index % 5) * 0.32,
      speed: 0.002 + (index % 9) * 0.00035,
    }));

    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = window.innerWidth * ratio;
      canvas.height = window.innerHeight * ratio;
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${window.innerHeight}px`;
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    };

    const draw = (time = 0) => {
      if (time - lastDraw < 33) {
        animation = requestAnimationFrame(draw);
        return;
      }
      lastDraw = time;
      frame += 1;
      const width = window.innerWidth;
      const height = window.innerHeight;
      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = 'lighter';
      particles.forEach((particle, index) => {
        const orbit = 80 + (index % 13) * 34;
        const cx = width * (0.18 + ((particle.seed % 17) / 25));
        const cy = height * (0.18 + ((particle.seed % 23) / 30));
        const x = cx + Math.cos(frame * particle.speed + particle.seed) * orbit;
        const y = cy + Math.sin(frame * particle.speed * 1.6 + particle.seed) * orbit * 0.52;
        const glow = ctx.createRadialGradient(x, y, 0, x, y, particle.radius * 11);
        glow.addColorStop(0, 'rgba(103, 232, 249, .32)');
        glow.addColorStop(0.45, 'rgba(168, 85, 247, .12)');
        glow.addColorStop(1, 'rgba(6, 182, 212, 0)');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, particle.radius * 11, 0, Math.PI * 2);
        ctx.fill();
      });
      animation = requestAnimationFrame(draw);
    };

    resize();
    draw();
    window.addEventListener('resize', resize);
    return () => {
      cancelAnimationFrame(animation);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="particle-canvas" aria-hidden="true" />;
}

function CursorAura() {
  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  const springX = useSpring(x, { stiffness: 120, damping: 24 });
  const springY = useSpring(y, { stiffness: 120, damping: 24 });
  const [enabled] = useState(() => (typeof window === 'undefined' ? true : !window.matchMedia('(pointer: coarse)').matches));

  useEffect(() => {
    if (!enabled) return undefined;
    const move = (event: MouseEvent) => {
      x.set(event.clientX - 180);
      y.set(event.clientY - 180);
    };
    window.addEventListener('mousemove', move);
    return () => window.removeEventListener('mousemove', move);
  }, [enabled, x, y]);

  if (!enabled) return null;
  return <motion.div className="cursor-aura" style={{ x: springX, y: springY }} aria-hidden="true" />;
}

function MetricRail({ data }: { data: NumerisData }) {
  const avgConfidence = data.signals.length
    ? Math.round(data.signals.reduce((sum, signal) => sum + signal.confidence, 0) / data.signals.length)
    : 0;
  const risk = data.signals.length ? Math.round(data.signals.reduce((sum, signal) => sum + signal.risk, 0) / data.signals.length) : 0;
  const moduleHealth = data.modules.length ? Math.round(data.modules.reduce((sum, module) => sum + module.metric, 0) / data.modules.length) : 0;

  return (
    <div className="metric-rail">
      <div><span>Agent Health</span><strong>{moduleHealth}%</strong></div>
      <div><span>Signal Conviction</span><strong>{avgConfidence}%</strong></div>
      <div><span>Exposure Risk</span><strong>{risk}%</strong></div>
      <div><span>Live Engines</span><strong>{data.simulations.length}</strong></div>
    </div>
  );
}

function LoadingExperience() {
  return (
    <div className="loading-shell">
      <div className="loading-orb" />
      <p>Waking Numeris intelligence fabric</p>
    </div>
  );
}

function PortfolioCommandDeck({ signals, events }: { signals: Signal[]; events: EventStreamItem[] }) {
  const topSignals = signals.slice(0, 5);
  const avgRisk = signals.length ? Math.round(signals.reduce((sum, signal) => sum + signal.risk, 0) / signals.length) : 0;
  const avgMomentum = signals.length ? Math.round(signals.reduce((sum, signal) => sum + signal.momentum, 0) / signals.length) : 0;
  const maxImpact = events.length ? Math.max(...events.map((event) => event.impact)) : 100;

  return (
    <section className="section command-deck-section" id="command-deck">
      <div className="section-kicker"><Network size={16} /> portfolio command deck</div>
      <div className="command-deck">
        <motion.div className="exposure-sphere" whileHover={{ scale: 1.025, rotateY: -4 }}>
          <div className="sphere-core">
            <span>Unified Exposure</span>
            <strong>{avgMomentum}%</strong>
            <small>Momentum field</small>
          </div>
          {topSignals.map((signal, index) => (
            <div className="sphere-node" style={{ '--node': index, '--risk': signal.risk } as React.CSSProperties} key={signal.id}>
              <b>{signal.symbol}</b>
              <span>{signal.confidence}%</span>
            </div>
          ))}
        </motion.div>
        <div className="deck-copy">
          <h2>Broker, risk, and signal layers fused into one spatial operating surface.</h2>
          <p>Designed for your Zerodha, Angel One, and ICICI Direct broker mesh: the frontend now feels more like a mission-critical trading cockpit than a dashboard.</p>
          <div className="deck-stat-grid">
            <div><span>Avg Risk</span><strong>{avgRisk}%</strong></div>
            <div><span>Event Max</span><strong>{maxImpact}%</strong></div>
            <div><span>Signal Mesh</span><strong>{signals.length}</strong></div>
          </div>
        </div>
      </div>
    </section>
  );
}

function EventStream({ events }: { events: EventStreamItem[] }) {
  return (
    <section className="section event-stream-section" id="events">
      <div className="section-kicker"><RadioTower size={16} /> intelligence event stream</div>
      <div className="section-heading">
        <h2>Real-time system narrative with impact telemetry.</h2>
        <p>A premium, animated feed makes the backend intelligence fabric visible: risk pulses, broker normalization, swarm syncs, and WorldMonitor alerts.</p>
      </div>
      <div className="event-timeline">
        {events.map((event, index) => (
          <motion.article
            className="event-card"
            key={event.id}
            initial={{ opacity: 0, y: 44, scale: 0.96 }}
            whileInView={{ opacity: 1, y: 0, scale: 1 }}
            viewport={{ once: true, amount: 0.35 }}
            transition={{ delay: index * 0.07 }}
          >
            <div className="event-impact" style={{ '--impact': event.impact } as React.CSSProperties}>
              <span>{event.impact}</span>
            </div>
            <div>
              <span>{event.event_type} · {event.region}</span>
              <h3>{event.title}</h3>
              <p>{event.detail}</p>
            </div>
          </motion.article>
        ))}
      </div>
    </section>
  );
}

function NeuralMarketMap({ signals }: { signals: Signal[] }) {
  const nodes = signals.slice(0, 8).map((signal, index) => ({
    ...signal,
    x: 12 + ((index * 31) % 76),
    y: 18 + ((index * 47) % 64),
  }));

  return (
    <div className="neural-map" aria-label="Neural market probability map">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none">
        {nodes.slice(1).map((node, index) => (
          <motion.line
            key={`${node.symbol}-line`}
            x1={nodes[0]?.x || 50}
            y1={nodes[0]?.y || 50}
            x2={node.x}
            y2={node.y}
            initial={{ pathLength: 0, opacity: 0 }}
            whileInView={{ pathLength: 1, opacity: 0.55 }}
            viewport={{ once: true }}
            transition={{ delay: index * 0.08, duration: 0.9 }}
          />
        ))}
      </svg>
      {nodes.map((node, index) => (
        <motion.div
          className="neural-node"
          key={node.id}
          style={{ left: `${node.x}%`, top: `${node.y}%`, '--confidence': node.confidence } as React.CSSProperties}
          initial={{ scale: 0, opacity: 0 }}
          whileInView={{ scale: 1, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: index * 0.06, type: 'spring', stiffness: 120 }}
        >
          <strong>{node.symbol}</strong>
          <span>{node.confidence}%</span>
        </motion.div>
      ))}
      <div className="neural-caption">
        <b>AI reasoning graph</b>
        <span>Conviction, risk, and momentum clustered as a living market map.</span>
      </div>
    </div>
  );
}

function GeopoliticalNews({ news, loading }: { news: GeoNewsItem[]; loading: boolean }) {
  const strongest = news.length ? news.reduce((max, item) => (item.impact > max.impact ? item : max), news[0]) : null;

  return (
    <section className="section geopolitical-section" id="geopolitics">
      <div className="section-kicker"><Newspaper size={16} /> geopolitical news</div>
      <div className="geo-layout">
        <div className="geo-briefing">
          <h2>WorldMonitor geopolitical briefing, connected to live global news.</h2>
          <p>Powered by a secure FastAPI GDELT integration with Supabase caching. Numeris scores each story for market impact and routes it into the geopolitical risk surface.</p>
          {strongest && (
            <div className="geo-spotlight">
              <span>Highest impact now</span>
              <strong>{strongest.impact}%</strong>
              <p>{strongest.title}</p>
            </div>
          )}
        </div>
        <div className="geo-news-grid">
          {loading && <div className="geo-loading">Fetching WorldMonitor news feed...</div>}
          {!loading && news.map((item, index) => (
            <motion.a
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="geo-news-card"
              key={`${item.id}-${item.url}`}
              initial={{ opacity: 0, y: 34 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.25 }}
              transition={{ delay: index * 0.05 }}
            >
              <div className="geo-impact" style={{ '--impact': item.impact } as React.CSSProperties}><span>{item.impact}</span></div>
              <div>
                <span>{item.region} · {item.source}</span>
                <h3>{item.title}</h3>
                <p>{item.summary}</p>
                <b>{new Date(item.published_at).toLocaleString()} <ExternalLink size={14} /></b>
              </div>
            </motion.a>
          ))}
        </div>
      </div>
    </section>
  );
}

function ModuleConstellation({ modules }: { modules: Module[] }) {
  return (
    <section className="section constellation-section" id="swarm">
      <div className="section-kicker"><Sparkles size={16} /> autonomous agents</div>
      <div className="section-heading">
        <h2>Specialized intelligence, staged like a command deck.</h2>
        <p>Every card is fed through the Numeris FastAPI backend, giving the frontend a living architecture map instead of decorative filler.</p>
      </div>
      <div className="constellation-grid">
        {modules.map((module, index) => (
          <motion.article
            key={module.id}
            className="agent-card"
            initial={{ opacity: 0, y: 44, rotateX: -14 }}
            whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ delay: index * 0.06, duration: 0.7, ease: [0.2, 0.8, 0.2, 1] }}
            whileHover={{ y: -12, rotateX: 8, rotateY: -7, scale: 1.02 }}
          >
            <div className="agent-card-glow" style={{ background: module.gradient }} />
            <div className="agent-topline">
              <span>{module.domain}</span>
              <b>{module.metric}%</b>
            </div>
            <h3>{module.name}</h3>
            <p>{module.description}</p>
            <div className="agent-footer">
              <span className="pulse-dot" />
              {module.status}
            </div>
          </motion.article>
        ))}
      </div>
    </section>
  );
}

function MarketDashboard({ signals }: { signals: Signal[] }) {
  const featuredSymbol = signals[0]?.symbol || 'AAPL';
  return (
    <section className="section market-section" id="markets">
      <div className="section-kicker"><TrendingUp size={16} /> market dashboard</div>
      <div className="dashboard-shell">
        <div className="signal-board">
          <div className="section-heading compact">
            <h2>Signal feed with kinetic conviction mapping.</h2>
            <p>Technical, sentiment, and risk outputs are presented as glass instruments for fast executive scanning.</p>
          </div>
          <div className="signal-list">
            {signals.map((signal) => (
              <motion.div className="signal-row" key={signal.id} whileHover={{ x: 8 }}>
                <div>
                  <strong>{signal.symbol}</strong>
                  <span>{signal.agent}</span>
                </div>
                <div className="verdict">{signal.verdict}</div>
                <div className="bar-wrap"><span style={{ width: `${signal.confidence}%` }} /></div>
                <b>{signal.confidence}%</b>
              </motion.div>
            ))}
          </div>
        </div>
        <div className="chart-pod">
          <MarketCandlestickChart symbol={featuredSymbol} />
          <NeuralMarketMap signals={signals} />
          <div className="radar-card">
            <Radar />
            <div><strong>Predictive spread</strong><span>Risk-adjusted momentum paired with zoomable candlestick structure.</span></div>
          </div>
        </div>
      </div>
    </section>
  );
}

function SimulationLab({ simulations, onTune }: { simulations: Simulation[]; onTune: (id: number, intensity: number) => Promise<void> }) {
  return (
    <section className="section simulation-section" id="simulations">
      <div className="section-kicker"><Globe2 size={16} /> simulation lab</div>
      <div className="section-heading">
        <h2>Mirofish and WorldMonitor controls that feel alive.</h2>
        <p>Each intensity slider persists through the Supabase-backed API, so operators can shape the simulation state directly from the frontend.</p>
      </div>
      <div className="simulation-grid">
        {simulations.map((sim) => (
          <motion.article className="simulation-card" key={sim.id} whileHover={{ rotateY: 6, rotateX: -4, y: -10 }}>
            <div className="sim-orb"><Waves /></div>
            <div className="sim-meta"><span>{sim.engine}</span><b>{sim.region}</b></div>
            <h3>{sim.name}</h3>
            <p>{sim.forecast}</p>
            <label>
              <span>Scenario intensity</span>
              <strong>{sim.intensity}%</strong>
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={sim.intensity}
              onChange={(event) => onTune(sim.id, Number(event.target.value))}
            />
          </motion.article>
        ))}
      </div>
    </section>
  );
}

function IntelligenceVault({ reports }: { reports: Report[] }) {
  return (
    <section className="section vault-section" id="vault">
      <div className="vault-copy">
        <div className="section-kicker"><Layers3 size={16} /> intelligence vault</div>
        <h2>Research, risk alerts, and operator-ready intelligence.</h2>
        <p>The vault transforms backend reports into a cinematic briefing wall with severity, category, and generation cadence visible at a glance.</p>
      </div>
      <div className="report-stack">
        {reports.map((report, index) => (
          <motion.article
            className="report-card"
            key={report.id}
            initial={{ opacity: 0, x: 60 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ delay: index * 0.08 }}
          >
            <span className={`severity severity-${report.severity.toLowerCase()}`}>{report.severity}</span>
            <h3>{report.title}</h3>
            <p>{report.summary}</p>
            <div><span>{report.category}</span><time>{new Date(report.created_at).toLocaleDateString()}</time></div>
          </motion.article>
        ))}
      </div>
    </section>
  );
}

function AgentTerminal({ interactions, onSend, onDelete }: { interactions: Interaction[]; onSend: (prompt: string) => Promise<void>; onDelete: (id: number) => Promise<void> }) {
  const [prompt, setPrompt] = useState('');
  const [sending, setSending] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!prompt.trim() || sending) return;
    setSending(true);
    await onSend(prompt);
    setPrompt('');
    setSending(false);
  };

  return (
    <section className="section terminal-section" id="terminal">
      <div className="terminal-shell">
        <div className="terminal-header">
          <div>
            <span><Command size={16} /> agent terminal</span>
            <h2>Ask the swarm. Watch the interface respond.</h2>
          </div>
          <button className="voice-button" type="button"><Mic2 size={18} /> Voice Control</button>
        </div>
        <div className="terminal-feed">
          {interactions.map((item) => (
            <motion.div className="terminal-message" key={item.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
              <div className="user-line"><span>Operator</span><p>{item.prompt}</p></div>
              <div className="agent-line">
                <div><BrainCircuit size={18} /><strong>{item.agent}</strong><b>{item.confidence}%</b></div>
                <p>{item.response}</p>
                <button type="button" onClick={() => onDelete(item.id)} aria-label="Delete terminal exchange"><Trash2 size={15} /></button>
              </div>
            </motion.div>
          ))}
        </div>
        <form className="terminal-input" onSubmit={submit}>
          <input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Ask about risk, geopolitics, portfolio allocation, or sentiment..." />
          <button type="submit" disabled={sending}><Send size={18} /> {sending ? 'Routing' : 'Send'}</button>
        </form>
      </div>
    </section>
  );
}

export default function App() {
  const { authStatus, role, signOut } = useAuth();
  const [showAdminModal, setShowAdminModal] = useState(false);
  const [data, setData] = useState<NumerisData>(initialData);
  const [geoNews, setGeoNews] = useState<GeoNewsItem[]>([]);
  const [newsLoading, setNewsLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadNumeris = useCallback(async () => {
    if (authStatus !== 'unlocked') return;
    try {
      const payload = await getNumerisDashboard();
      setData(payload);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [authStatus]);

  useEffect(() => {
    if (authStatus !== 'unlocked') return;
    let cancelled = false;
    getNumerisDashboard()
      .then((payload) => {
        if (!cancelled) {
          setData(payload);
          setError('');
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authStatus]);

  useEffect(() => {
    if (authStatus !== 'unlocked') return;
    let cancelled = false;
    getGeopoliticalNews()
      .then((payload) => {
        if (!cancelled) setGeoNews(payload);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Unknown geopolitical news error');
      })
      .finally(() => {
        if (!cancelled) setNewsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authStatus]);

  const sendPrompt = async (prompt: string) => {
    await sendNumerisPrompt(prompt);
    await loadNumeris();
  };

  const tuneSimulation = async (id: number, intensity: number) => {
    setData((current) => ({
      ...current,
      simulations: current.simulations.map((simulation) => (simulation.id === id ? { ...simulation, intensity } : simulation)),
    }));
    await tuneNumerisSimulation(id, intensity);
    await loadNumeris();
  };

  const deleteInteraction = async (id: number) => {
    await deleteNumerisInteraction(id);
    await loadNumeris();
  };

  if (authStatus === 'loading') {
    return <LoadingExperience />;
  }

  if (authStatus === 'unauthenticated') {
    return (
      <main className="app-shell">
        <ParticleCanvas />
        <CursorAura />
        <AuthScreen />
      </main>
    );
  }

  if (authStatus === 'access-locked') {
    return (
      <main className="app-shell">
        <ParticleCanvas />
        <CursorAura />
        <AccessCodeScreen />
      </main>
    );
  }

  if (loading) return <LoadingExperience />;

  return (
    <main className="app-shell">
      <EntranceExperience />
      <ParticleCanvas />
      <CursorAura />
      <nav className="top-nav">
        <a href="#top" className="brand"><span>N</span> Numeris</a>
        <div className="nav-links">
          <a href="#swarm">Swarm</a>
          <a href="#portfolio">Portfolio</a>
          <a href="#command-deck">Deck</a>
          <a href="#markets">Markets</a>
          <a href="#geopolitics">Geopolitics</a>
          <a href="#simulations">Lab</a>
          <a href="#events">Events</a>
          <a href="#vault">Vault</a>
          <a href="#terminal">Terminal</a>
          {role === 'admin' && (
            <button onClick={() => setShowAdminModal(true)} className="nav-admin-btn">
              Console
            </button>
          )}
          <button onClick={signOut} className="nav-logout-btn">
            Sign Out
          </button>
        </div>
      </nav>
      <ScrollProgress />

      {error && <div className="error-banner">{error}</div>}

      <header className="hero" id="top">
        <div className="hero-ambient-stage" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div className="hero-neural-effects" aria-hidden="true">
          <span className="hero-neural-effects__beam" />
          <span className="hero-neural-effects__orb hero-neural-effects__orb--one" />
          <span className="hero-neural-effects__orb hero-neural-effects__orb--two" />
          <span className="hero-neural-effects__chip hero-neural-effects__chip--one">RAG MEMORY ONLINE</span>
          <span className="hero-neural-effects__chip hero-neural-effects__chip--two">WORLD RISK SYNC</span>
          <span className="hero-neural-effects__chip hero-neural-effects__chip--three">AGENT CONSENSUS</span>
        </div>
        <div className="hero-copy">
          <motion.div className="hero-badge" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 3.1, duration: 0.8 }}>
            <ShieldCheck size={16} /> Security-first financial intelligence OS
          </motion.div>
          <motion.h1 className="hero-title" initial="hidden" animate="show" variants={{ show: { transition: { staggerChildren: 0.055, delayChildren: 3.2 } }, hidden: {} }}>
            {['Autonomous', 'market', 'intelligence,', 'made', 'visible.'].map((word) => (
              <motion.span
                key={word}
                variants={{ hidden: { opacity: 0, y: 44, rotateX: -72, filter: 'blur(10px)' }, show: { opacity: 1, y: 0, rotateX: 0, filter: 'blur(0px)' } }}
                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              >
                {word}
              </motion.span>
            ))}
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 34 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 3.65, duration: 0.85 }}>
            Numeris visualizes your FastAPI, Celery, ChromaDB, Mirofish, and WorldMonitor backend as a high-trust control room for traders, analysts, and risk teams.
          </motion.p>
          <motion.div className="hero-actions" initial={{ opacity: 0, y: 34 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 3.78, duration: 0.85 }}>
            <a href="#terminal">Launch terminal <ArrowUpRight size={18} /></a>
            <a href="#brain-atlas">Explore cortex map</a>
            <a href="#markets">View live intelligence</a>
          </motion.div>
          <MetricRail data={data} />
        </div>
        <div className="hero-visual">
          <RealisticHollowBrain />
        </div>
      </header>

      <BrainAtlas regions={data.brainRegions} />
      <ManualPortfolio />
      <ModuleConstellation modules={data.modules} />
      <PortfolioCommandDeck signals={data.signals} events={data.events} />
      <MarketDashboard signals={data.signals} />
      <GeopoliticalNews news={geoNews} loading={newsLoading} />
      <SimulationLab simulations={data.simulations} onTune={tuneSimulation} />
      <EventStream events={data.events} />
      <IntelligenceVault reports={data.reports} />
      <AgentTerminal interactions={data.interactions} onSend={sendPrompt} onDelete={deleteInteraction} />

      <AdminPanel isOpen={showAdminModal} onClose={() => setShowAdminModal(false)} />
      <style>{`
        .nav-links {
          display: flex;
          align-items: center;
          gap: 1.25rem;
        }
        .nav-admin-btn {
          background: rgba(6, 182, 212, 0.12);
          border: 1px solid rgba(6, 182, 212, 0.3);
          color: #22d3ee;
          padding: 0.35rem 0.75rem;
          border-radius: 6px;
          font-size: 0.82rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }
        .nav-admin-btn:hover {
          background: rgba(6, 182, 212, 0.25);
          box-shadow: 0 0 12px rgba(6, 182, 212, 0.2);
        }
        .nav-logout-btn {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.25);
          color: #f87171;
          padding: 0.35rem 0.75rem;
          border-radius: 6px;
          font-size: 0.82rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }
        .nav-logout-btn:hover {
          background: rgba(239, 68, 68, 0.2);
          color: #ef4444;
        }
      `}</style>
    </main>
  );
}
