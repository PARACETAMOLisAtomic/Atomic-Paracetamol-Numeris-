import { motion } from 'framer-motion';
import { BrainCircuit, ExternalLink } from 'lucide-react';

export type BrainRegion = {
  id: number;
  name: string;
  system: string;
  description: string;
  section_id: string;
  x: number;
  y: number;
  position_order: number;
};

export default function BrainAtlas({ regions }: { regions: BrainRegion[] }) {
  const scrollToSection = (sectionId: string) => {
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <section className="section brain-atlas-section" id="brain-atlas">
      <div className="section-kicker"><BrainCircuit size={16} /> Numeris cortex map</div>
      <div className="brain-atlas-shell">
        <div className="brain-atlas-copy">
          <h2>The website becomes a brain. Every product surface lives inside a cognitive region.</h2>
          <p>
            Click any neural region to jump through Numeris: memory, analysis, risk, geopolitics, simulation, portfolio, terminal, and swarm orchestration are mapped onto a realistic cortex.
          </p>
        </div>

        <motion.div
          className="brain-atlas-visual"
          initial={{ opacity: 0, y: 40, scale: 0.96 }}
          whileInView={{ opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: true, amount: 0.35 }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="brain-atlas-orbit brain-atlas-orbit-one" />
          <div className="brain-atlas-orbit brain-atlas-orbit-two" />
          <img src="/images/numeris-hollow-brain.png" alt="Numeris interactive brain atlas" />
          <svg className="brain-atlas-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            {regions.map((region) => (
              <motion.line
                key={region.id}
                x1="50"
                y1="50"
                x2={region.x}
                y2={region.y}
                initial={{ pathLength: 0, opacity: 0 }}
                whileInView={{ pathLength: 1, opacity: 0.52 }}
                viewport={{ once: true }}
                transition={{ delay: region.position_order * 0.04, duration: 0.85 }}
              />
            ))}
          </svg>
          {regions.map((region) => (
            <motion.button
              type="button"
              className="brain-region-hotspot"
              key={region.id}
              style={{ left: `${region.x}%`, top: `${region.y}%` }}
              onClick={() => scrollToSection(region.section_id)}
              initial={{ opacity: 0, scale: 0 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 + region.position_order * 0.06, type: 'spring', stiffness: 150 }}
              whileHover={{ scale: 1.12, y: -4 }}
            >
              <span>{region.name}</span>
              <strong>{region.system}</strong>
              <ExternalLink size={13} />
            </motion.button>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
