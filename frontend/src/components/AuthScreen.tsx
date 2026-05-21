import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LogIn, UserPlus, Eye, EyeOff, ShieldAlert } from 'lucide-react';
import { supabase } from '../lib/supabase';

interface AuthScreenProps {
  onSuccess?: () => void;
}

export const AuthScreen: React.FC<AuthScreenProps> = ({ onSuccess }) => {
  const [activeTab, setActiveTab] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const validateInputs = () => {
    if (!email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      setErrorMessage('Please enter a valid email address.');
      return false;
    }
    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters long.');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    if (!validateInputs()) return;

    if (!supabase) {
      setErrorMessage('Authentication service is currently unconfigured. Running in fallback offline mode.');
      return;
    }

    setLoading(true);
    try {
      if (activeTab === 'login') {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        onSuccess?.();
      } else {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
        });
        if (error) throw error;
        
        // Supabase sign up might require email confirmation
        if (data.session) {
          setSuccessMessage('Registration successful! Accessing platform...');
          onSuccess?.();
        } else {
          setSuccessMessage('Registration successful! Please check your email for confirmation link.');
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Authentication error. Please check your credentials.';
      setErrorMessage(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <motion.div
        className="auth-card"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        <div className="auth-header">
          <div className="auth-brand">
            <span className="brand-dot" />
            <h2>NUMERIS</h2>
          </div>
          <p className="auth-tagline">PLATFORM INTEGRATED INTELLIGENCE</p>
        </div>

        <div className="tab-buttons">
          <button
            type="button"
            className={`tab-btn ${activeTab === 'login' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('login');
              setErrorMessage('');
              setSuccessMessage('');
            }}
          >
            <LogIn size={16} />
            <span>Sign In</span>
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'signup' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('signup');
              setErrorMessage('');
              setSuccessMessage('');
            }}
          >
            <UserPlus size={16} />
            <span>Register</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="email-input">Email Address</label>
            <input
              id="email-input"
              type="email"
              placeholder="name@domain.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password-input">Password</label>
            <div className="password-wrapper">
              <input
                id="password-input"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <AnimatePresence mode="wait">
            {errorMessage && (
              <motion.div
                className="alert error-alert"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <ShieldAlert size={16} />
                <span>{errorMessage}</span>
              </motion.div>
            )}

            {successMessage && (
              <motion.div
                className="alert success-alert"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <ShieldAlert size={16} style={{ color: '#10b981' }} />
                <span>{successMessage}</span>
              </motion.div>
            )}
          </AnimatePresence>

          <button type="submit" className="submit-btn" disabled={loading}>
            {loading ? (
              <span className="spinner" />
            ) : activeTab === 'login' ? (
              'Authenticate Session'
            ) : (
              'Establish Credentials'
            )}
          </button>
        </form>
      </motion.div>

      <style>{`
        .auth-container {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 100vh;
          padding: 2rem;
          position: relative;
          z-index: 10;
        }
        .auth-card {
          width: 100%;
          max-width: 440px;
          background: rgba(8, 12, 28, 0.65);
          backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          padding: 2.5rem 2rem;
          box-shadow: 
            0 20px 40px rgba(0, 0, 0, 0.5),
            0 0 100px rgba(14, 165, 233, 0.03);
        }
        .auth-header {
          text-align: center;
          margin-bottom: 2rem;
        }
        .auth-brand {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          margin-bottom: 0.5rem;
        }
        .brand-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #06b6d4;
          box-shadow: 0 0 12px #06b6d4;
        }
        .auth-brand h2 {
          font-family: 'Space Grotesk', sans-serif;
          font-size: 1.8rem;
          font-weight: 700;
          letter-spacing: 0.15em;
          color: #ffffff;
          margin: 0;
        }
        .auth-tagline {
          font-size: 0.72rem;
          font-weight: 600;
          letter-spacing: 0.25em;
          color: #64748b;
          margin: 0;
        }
        .tab-buttons {
          display: grid;
          grid-template-columns: 1fr 1fr;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.05);
          padding: 4px;
          border-radius: 10px;
          margin-bottom: 2rem;
        }
        .tab-btn {
          background: none;
          border: none;
          color: #94a3b8;
          padding: 0.6rem;
          border-radius: 8px;
          font-size: 0.88rem;
          font-weight: 500;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          transition: all 0.25s ease;
        }
        .tab-btn:hover {
          color: #ffffff;
        }
        .tab-btn.active {
          background: rgba(255, 255, 255, 0.07);
          color: #ffffff;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }
        .auth-form {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }
        .form-group {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        .form-group label {
          font-size: 0.8rem;
          font-weight: 500;
          color: #94a3b8;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .form-group input {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 10px;
          padding: 0.75rem 1rem;
          color: #ffffff;
          outline: none;
          font-size: 0.95rem;
          transition: all 0.25s ease;
        }
        .form-group input:focus {
          border-color: rgba(6, 182, 212, 0.6);
          background: rgba(6, 182, 212, 0.02);
          box-shadow: 0 0 16px rgba(6, 182, 212, 0.08);
        }
        .password-wrapper {
          position: relative;
          display: flex;
          align-items: center;
        }
        .password-wrapper input {
          width: 100%;
          padding-right: 2.75rem;
        }
        .password-toggle {
          position: absolute;
          right: 12px;
          background: none;
          border: none;
          color: #64748b;
          cursor: pointer;
          padding: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: color 0.2s;
        }
        .password-toggle:hover {
          color: #ffffff;
        }
        .submit-btn {
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
          box-shadow: 0 8px 24px rgba(8, 145, 178, 0.25);
        }
        .submit-btn:hover:not(:disabled) {
          filter: brightness(1.1);
          transform: translateY(-1px);
          box-shadow: 0 8px 30px rgba(8, 145, 178, 0.35);
        }
        .submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .alert {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 0.75rem 1rem;
          border-radius: 10px;
          font-size: 0.85rem;
          line-height: 1.4;
          overflow: hidden;
        }
        .error-alert {
          border: 1px solid rgba(239, 68, 68, 0.25);
          background: rgba(239, 68, 68, 0.06);
          color: #fca5a5;
        }
        .success-alert {
          border: 1px solid rgba(16, 185, 129, 0.25);
          background: rgba(16, 185, 129, 0.06);
          color: #a7f3d0;
        }
        .spinner {
          width: 20px;
          height: 20px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: #ffffff;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
          to { rotate: 360deg; }
        }
      `}</style>
    </div>
  );
};
