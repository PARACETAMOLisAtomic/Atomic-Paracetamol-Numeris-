import { motion } from 'framer-motion';
import { BrainCircuit } from 'lucide-react';

export type BrainTrait = {
  id: number;
  title: string;
  label: string;
  description: string;
  confidence: number;
  priority: number;
};

export default function RealisticHollowBrain() {
  return (
    <div className="brain-command-visual">
      <motion.div
        className="brain-specimen"
        initial={{ opacity: 0, scale: 0.92, rotateY: -18 }}
        animate={{ opacity: 1, scale: 1, rotateY: 0 }}
        transition={{ duration: 1.1, ease: [0.2, 0.8, 0.2, 1] }}
      >
        <div className="brain-halo brain-halo-one" />
        <div className="brain-halo brain-halo-two" />
        <div className="brain-glass-shell">
          <img src="/images/numeris-hollow-brain.png" alt="Numeris neural brain visualization" />
          <div className="brain-fallback" aria-hidden="true">
            <BrainCircuit size={148} />
          </div>
        </div>
        <svg className="brain-wireframe" viewBox="0 0 520 520" aria-hidden="true">
          <defs>
            <linearGradient id="brainStroke" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0" stopColor="#67e8f9" />
              <stop offset="0.55" stopColor="#a78bfa" />
              <stop offset="1" stopColor="#f472b6" />
            </linearGradient>
          </defs>
          <path d="M125 280C75 245 84 145 162 122C181 62 280 60 310 116C377 101 438 157 424 223C481 257 456 354 383 366C359 439 259 456 215 399C143 412 91 343 125 280Z" />
          <path d="M153 270C205 248 194 183 242 168C302 150 319 214 374 205" />
          <path d="M156 322C224 289 274 361 352 326" />
          <path d="M213 133C202 198 249 229 230 292C213 348 248 382 296 405" />
          <path d="M313 116C286 172 348 200 329 260C309 324 365 348 383 366" />
        </svg>
      </motion.div>
    </div>
  );
}
