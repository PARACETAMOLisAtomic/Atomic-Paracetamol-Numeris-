import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { BrainCircuit, CheckCircle2 } from 'lucide-react';
import { getEntranceSequence } from '../lib/api';
import './EntranceExperience.css';

export type EntranceSequence = {
  id: number;
  label: string;
  value: string;
  sequence_order: number;
};

const fallbackSequence: EntranceSequence[] = [
  { id: 1, label: 'Security', value: 'verified', sequence_order: 1 },
  { id: 2, label: 'Memory', value: 'hydrated', sequence_order: 2 },
  { id: 3, label: 'World', value: 'synced', sequence_order: 3 },
  { id: 4, label: 'Swarm', value: 'awake', sequence_order: 4 },
];

export default function EntranceExperience() {
  const [items, setItems] = useState<EntranceSequence[]>([]);
  const [visible, setVisible] = useState(true);
  const [opening, setOpening] = useState(false);
  const [hovered, setHovered] = useState(false);
  const brainRef = useRef<HTMLButtonElement | null>(null);

  const sequence = items.length ? items.slice(0, 4) : fallbackSequence;
  const sparks = useMemo(
    () => Array.from({ length: 18 }, (_, index) => ({
      id: index,
      angle: index * 20,
      radius: 110 + (index % 4) * 24,
      delay: index * 0.035,
    })),
    [],
  );

  useEffect(() => {
    let cancelled = false;
    getEntranceSequence()
      .then((payload) => {
        if (!cancelled) setItems(payload);
      })
      .catch((error: unknown) => {
        console.error('Entrance sequence fetch failed:', error);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const openBrain = () => {
    if (opening) return;
    setOpening(true);
    window.setTimeout(() => setVisible(false), 1250);
  };

  const updatePointer = (event: React.MouseEvent<HTMLButtonElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const pointerX = (event.clientX - rect.left) / rect.width - 0.5;
    const pointerY = (event.clientY - rect.top) / rect.height - 0.5;
    event.currentTarget.style.setProperty('--tilt-x', `${pointerY * -6}deg`);
    event.currentTarget.style.setProperty('--tilt-y', `${pointerX * 6}deg`);
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.section
          className={`cortex-portal ${opening ? 'cortex-portal--opening' : ''}`}
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.45, ease: 'easeOut' }}
          aria-label="Open Numeris cortex portal"
        >
          <motion.div
            className="cortex-portal__veil"
            animate={opening ? { opacity: 0 } : { opacity: 1 }}
            transition={{ duration: 0.75, ease: [0.76, 0, 0.24, 1] }}
          />

          <motion.div
            className="cortex-portal__brand"
            initial={{ opacity: 0, y: -14 }}
            animate={opening ? { opacity: 0, y: -18 } : { opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.55 }}
          >
            <span>A</span>
            <b>Numeris</b>
          </motion.div>

          <motion.button
            ref={brainRef}
            type="button"
            className="cortex-portal__brain"
            onClick={openBrain}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => {
              setHovered(false);
              brainRef.current?.style.setProperty('--tilt-x', '0deg');
              brainRef.current?.style.setProperty('--tilt-y', '0deg');
            }}
            onMouseMove={updatePointer}
            onFocus={() => setHovered(true)}
            onBlur={() => setHovered(false)}
            aria-label="Enter through the Numeris cortex"
            animate={opening ? { scale: 5.2, opacity: 0, filter: 'blur(18px)' } : { scale: hovered ? 1.035 : 1, opacity: 1, filter: 'blur(0px)' }}
            transition={{ duration: opening ? 1.05 : 0.42, ease: [0.76, 0, 0.24, 1] }}
          >
            <div className="cortex-portal__aura" />
            <div className="cortex-portal__ring cortex-portal__ring--outer" />
            <div className="cortex-portal__ring cortex-portal__ring--inner" />
            <motion.img
              src="/images/numeris-hollow-brain.png"
              alt="Numeris cortex portal"
              draggable="false"
              animate={opening ? { rotate: 2 } : { rotate: hovered ? 1.2 : 0 }}
              transition={{ duration: 0.5 }}
            />
            <motion.div
              className="cortex-portal__core"
              animate={opening ? { scale: 0.2, opacity: 0 } : { scale: hovered ? 1.1 : 1, opacity: 1 }}
              transition={{ duration: 0.35 }}
            >
              <BrainCircuit size={30} />
            </motion.div>
            {sparks.map((spark) => (
              <motion.span
                className="cortex-portal__spark"
                key={spark.id}
                style={{ '--angle': `${spark.angle}deg`, '--radius': `${spark.radius}px` } as React.CSSProperties}
                initial={{ opacity: 0, scale: 0 }}
                animate={opening ? { opacity: [0, 1, 0], scale: [0, 1, 0.4], x: Math.cos((spark.angle * Math.PI) / 180) * spark.radius, y: Math.sin((spark.angle * Math.PI) / 180) * spark.radius } : { opacity: hovered ? 0.55 : 0.18, scale: hovered ? 1 : 0.72, x: Math.cos((spark.angle * Math.PI) / 180) * (spark.radius * 0.42), y: Math.sin((spark.angle * Math.PI) / 180) * (spark.radius * 0.42) }}
                transition={{ delay: opening ? spark.delay : 0, duration: opening ? 0.7 : 0.45, ease: 'easeOut' }}
              />
            ))}
          </motion.button>

          <motion.div
            className="cortex-portal__copy"
            initial={{ opacity: 0, y: 20 }}
            animate={opening ? { opacity: 0, y: 18 } : { opacity: 1, y: 0 }}
            transition={{ delay: opening ? 0 : 0.35, duration: 0.65 }}
          >
            <div className="cortex-portal__kicker">click the cortex</div>
            <h1>Open the intelligence layer.</h1>
            <p>A smooth neural handoff into Numeris market, risk, memory, simulation, and agent systems.</p>
          </motion.div>

          <motion.div
            className="cortex-portal__status"
            initial={{ opacity: 0, y: 18 }}
            animate={opening ? { opacity: 0, y: 18 } : { opacity: 1, y: 0 }}
            transition={{ delay: opening ? 0 : 0.62, duration: 0.55 }}
          >
            {sequence.map((item) => (
              <article key={item.id}>
                <CheckCircle2 size={14} />
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </article>
            ))}
          </motion.div>

          <motion.div
            className="cortex-portal__reveal"
            initial={{ scale: 0, opacity: 0 }}
            animate={opening ? { scale: [0, 1.15, 2.8], opacity: [0, 0.9, 0] } : { scale: 0, opacity: 0 }}
            transition={{ duration: 1.08, ease: [0.76, 0, 0.24, 1] }}
          />
        </motion.section>
      )}
    </AnimatePresence>
  );
}
