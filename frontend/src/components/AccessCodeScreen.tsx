import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, ShieldAlert, KeyRound, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AccessCodeScreen: React.FC = () => {
  const { redeemCode, signOut } = useAuth();
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) return;

    setError('');
    setLoading(true);
    try {
      const success = await redeemCode(code.trim());
      if (!success) {
        setError('The access code provided is invalid, deactivated, or expired.');
      }
    } catch {
      setError('An error occurred during code validation. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="access-gate-container">
      <motion.div
        className="access-gate-card"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.45, ease: 'easeOut' }}
      >
        <div className="gate-icon-wrapper">
          <KeyRound size={28} className="gate-icon" />
        </div>

        <div className="gate-header">
          <h2>Private Access Gated</h2>
          <p>
            Numeris v3.0 is currently restricted. Please enter a valid administrator invite code to proceed.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="gate-form">
          <div className="input-wrapper">
            <input
              type="text"
              placeholder="NUM-XXXX-XXXX-XXXX"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={loading}
              autoFocus
              required
            />
          </div>

          <AnimatePresence mode="wait">
            {error && (
              <motion.div
                className="gate-alert gate-error"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <ShieldAlert size={16} />
                <span>{error}</span>
              </motion.div>
            )}
          </AnimatePresence>

          <button type="submit" className="gate-submit-btn" disabled={loading}>
            {loading ? (
              <span className="gate-spinner" />
            ) : (
              <>
                <ShieldCheck size={16} />
                <span>Unlock Platform Access</span>
              </>
            )}
          </button>
        </form>

        <div className="gate-footer">
          <button type="button" className="gate-logout-btn" onClick={signOut}>
            <LogOut size={14} />
            <span>Sign Out Session</span>
          </button>
        </div>
      </motion.div>

      <style>{`
        .access-gate-container {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          padding: 2rem;
          position: relative;
          z-index: 10;
        }
        .access-gate-card {
          width: 100%;
          max-width: 440px;
          background: rgba(8, 12, 28, 0.65);
          backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          padding: 3rem 2rem 2.5rem;
          box-shadow: 
            0 20px 40px rgba(0, 0, 0, 0.5),
            0 0 100px rgba(103, 232, 249, 0.02);
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .gate-icon-wrapper {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background: rgba(6, 182, 212, 0.08);
          border: 1px solid rgba(6, 182, 212, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 1.5rem;
          box-shadow: 0 0 20px rgba(6, 182, 212, 0.15);
        }
        .gate-icon {
          color: #06b6d4;
          filter: drop-shadow(0 0 8px #06b6d4);
        }
        .gate-header h2 {
          font-family: 'Space Grotesk', sans-serif;
          font-size: 1.5rem;
          font-weight: 600;
          color: #ffffff;
          margin: 0 0 0.75rem;
          letter-spacing: 0.02em;
        }
        .gate-header p {
          font-size: 0.9rem;
          color: #94a3b8;
          line-height: 1.5;
          margin: 0 0 2rem;
        }
        .gate-form {
          width: 100%;
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }
        .input-wrapper input {
          width: 100%;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 10px;
          padding: 0.85rem 1rem;
          color: #ffffff;
          text-align: center;
          outline: none;
          font-family: monospace;
          font-size: 1.05rem;
          letter-spacing: 0.05em;
          transition: all 0.25s ease;
        }
        .input-wrapper input:focus {
          border-color: rgba(6, 182, 212, 0.6);
          background: rgba(6, 182, 212, 0.02);
          box-shadow: 0 0 16px rgba(6, 182, 212, 0.08);
        }
        .gate-submit-btn {
          background: linear-gradient(135deg, #0891b2 0%, #0284c7 100%);
          color: #ffffff;
          border: none;
          border-radius: 10px;
          padding: 0.85rem;
          font-size: 0.95rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.25s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          box-shadow: 0 8px 24px rgba(8, 145, 178, 0.2);
        }
        .gate-submit-btn:hover:not(:disabled) {
          filter: brightness(1.1);
          transform: translateY(-1px);
          box-shadow: 0 8px 30px rgba(8, 145, 178, 0.3);
        }
        .gate-submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .gate-alert {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 0.75rem 1rem;
          border-radius: 10px;
          font-size: 0.85rem;
          line-height: 1.4;
          text-align: left;
        }
        .gate-error {
          border: 1px solid rgba(239, 68, 68, 0.25);
          background: rgba(239, 68, 68, 0.06);
          color: #fca5a5;
        }
        .gate-spinner {
          width: 20px;
          height: 20px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: #ffffff;
          border-radius: 50%;
          animation: gate-spin 0.8s linear infinite;
        }
        @keyframes gate-spin {
          to { rotate: 360deg; }
        }
        .gate-footer {
          margin-top: 2rem;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
          padding-top: 1.5rem;
          width: 100%;
        }
        .gate-logout-btn {
          background: none;
          border: none;
          color: #64748b;
          font-size: 0.82rem;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          transition: color 0.2s;
        }
        .gate-logout-btn:hover {
          color: #f43f5e;
        }
      `}</style>
    </div>
  );
};
