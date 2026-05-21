import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Plus, ToggleLeft, ToggleRight, RefreshCw, Shield, Key } from 'lucide-react';
import { getAdminCodes, generateAdminCodes, revokeAdminCode, type AdminCodeItem } from '../lib/api';

interface AdminPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AdminPanel: React.FC<AdminPanelProps> = ({ isOpen, onClose }) => {
  const [codes, setCodes] = useState<AdminCodeItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [generateRole, setGenerateRole] = useState<'admin' | 'beta_user' | 'standard_user'>('standard_user');
  const [generateCount, setGenerateCount] = useState(1);
  const [errorMessage, setErrorMessage] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchCodes = async () => {
    setLoading(true);
    setErrorMessage('');
    try {
      const data = await getAdminCodes();
      setCodes(data.codes || []);
    } catch {
      setErrorMessage('Failed to retrieve access codes from server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      const timer = setTimeout(() => {
        fetchCodes().catch((err) => {
          console.error(err);
        });
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    try {
      const response = await generateAdminCodes(generateRole, generateCount);
      if (response.status === 'success') {
        // Prepend new codes to state
        setCodes((prev) => [...response.codes, ...prev]);
      }
    } catch {
      setErrorMessage('Failed to generate invite codes.');
    }
  };

  const handleToggleActive = async (code: string, currentActive: boolean) => {
    setActionLoading(code);
    setErrorMessage('');
    try {
      const response = await revokeAdminCode(code, !currentActive);
      if (response.status === 'success') {
        setCodes((prev) =>
          prev.map((item) => (item.code === code ? { ...item, is_active: !currentActive } : item))
        );
      }
    } catch {
      setErrorMessage('Failed to update invite code status.');
    } finally {
      setActionLoading(null);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="admin-modal-overlay" onClick={onClose}>
        <motion.div
          className="admin-modal-card"
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.3 }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="modal-header">
            <div className="modal-title">
              <Shield size={20} className="shield-icon" />
              <h2>Access Control Console</h2>
            </div>
            <button className="close-btn" onClick={onClose}>
              <X size={18} />
            </button>
          </div>

          <div className="modal-body">
            {errorMessage && <div className="modal-error">{errorMessage}</div>}

            {/* Generator Form */}
            <form onSubmit={handleGenerate} className="generator-form">
              <div className="form-row">
                <div className="form-field">
                  <label htmlFor="gen-role">Assign Role</label>
                  <select
                    id="gen-role"
                    value={generateRole}
                    onChange={(e) => setGenerateRole(e.target.value as 'admin' | 'beta_user' | 'standard_user')}
                  >
                    <option value="standard_user">Standard User</option>
                    <option value="beta_user">Beta User</option>
                    <option value="admin">Administrator</option>
                  </select>
                </div>
                <div className="form-field">
                  <label htmlFor="gen-count">Batch Size</label>
                  <input
                    id="gen-count"
                    type="number"
                    min="1"
                    max="50"
                    value={generateCount}
                    onChange={(e) => setGenerateCount(Number(e.target.value))}
                  />
                </div>
                <button type="submit" className="gen-submit-btn">
                  <Plus size={16} />
                  <span>Generate Codes</span>
                </button>
              </div>
            </form>

            {/* Codes List */}
            <div className="codes-section">
              <div className="section-title">
                <h3>Active Access Codes</h3>
                <button type="button" className="refresh-btn" onClick={fetchCodes} disabled={loading}>
                  <RefreshCw size={14} className={loading ? 'spinning' : ''} />
                </button>
              </div>

              <div className="table-wrapper">
                {loading && codes.length === 0 ? (
                  <div className="list-loading">Querying secure records...</div>
                ) : codes.length === 0 ? (
                  <div className="list-empty">No access codes found. Create one above.</div>
                ) : (
                  <table className="codes-table">
                    <thead>
                      <tr>
                        <th>Access Code</th>
                        <th>Associated Role</th>
                        <th>Status</th>
                        <th>Created At</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {codes.map((item) => (
                        <tr key={item.code} className={!item.is_active ? 'inactive-row' : ''}>
                          <td className="code-cell">
                            <Key size={12} />
                            <code>{item.code}</code>
                          </td>
                          <td>
                            <span className={`role-badge role-${item.role}`}>
                              {item.role === 'admin' ? 'Admin' : item.role === 'beta_user' ? 'Beta' : 'User'}
                            </span>
                          </td>
                          <td>
                            <span className={`status-badge ${item.is_active ? 'status-active' : 'status-revoked'}`}>
                              {item.is_active ? 'Active' : 'Revoked'}
                            </span>
                          </td>
                          <td>{new Date(item.created_at).toLocaleDateString()}</td>
                          <td>
                            <button
                              type="button"
                              className="action-btn"
                              disabled={actionLoading === item.code}
                              onClick={() => handleToggleActive(item.code, item.is_active)}
                            >
                              {item.is_active ? (
                                <ToggleRight size={22} className="toggle-icon active" />
                              ) : (
                                <ToggleLeft size={22} className="toggle-icon revoked" />
                              )}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        </motion.div>

        <style>{`
          .admin-modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(2, 3, 10, 0.85);
            backdrop-filter: blur(8px);
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
          }
          .admin-modal-card {
            width: 100%;
            max-width: 800px;
            background: rgba(10, 15, 30, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            box-shadow: 
              0 30px 60px rgba(0, 0, 0, 0.6),
              0 0 100px rgba(6, 182, 212, 0.05);
            display: flex;
            flex-direction: column;
            max-height: 85vh;
            overflow: hidden;
          }
          .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1.5rem 2rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          }
          .modal-title {
            display: flex;
            align-items: center;
            gap: 10px;
          }
          .shield-icon {
            color: #06b6d4;
            filter: drop-shadow(0 0 8px #06b6d4);
          }
          .modal-title h2 {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.25rem;
            font-weight: 600;
            color: white;
            margin: 0;
          }
          .close-btn {
            background: none;
            border: none;
            color: #64748b;
            cursor: pointer;
            padding: 4px;
            display: flex;
            transition: color 0.2s;
          }
          .close-btn:hover {
            color: white;
          }
          .modal-body {
            padding: 2rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 2rem;
          }
          .modal-error {
            background: rgba(239, 68, 68, 0.06);
            border: 1px solid rgba(239, 68, 68, 0.2);
            color: #fca5a5;
            padding: 0.75rem 1rem;
            border-radius: 10px;
            font-size: 0.85rem;
          }
          .generator-form {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 1.25rem;
          }
          .form-row {
            display: grid;
            grid-template-columns: 2fr 1fr auto;
            gap: 1.25rem;
            align-items: flex-end;
          }
          @media (max-width: 600px) {
            .form-row {
              grid-template-columns: 1fr;
            }
          }
          .form-field {
            display: flex;
            flex-direction: column;
            gap: 6px;
          }
          .form-field label {
            font-size: 0.75rem;
            font-weight: 500;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
          }
          .form-field select, .form-field input {
            background: rgba(8, 10, 20, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: white;
            border-radius: 8px;
            padding: 0.6rem 0.8rem;
            outline: none;
            font-size: 0.9rem;
            transition: border-color 0.2s;
          }
          .form-field select:focus, .form-field input:focus {
            border-color: #06b6d4;
          }
          .gen-submit-btn {
            background: linear-gradient(135deg, #0891b2 0%, #0284c7 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.65rem 1.25rem;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            height: 38px;
          }
          .gen-submit-btn:hover {
            filter: brightness(1.1);
          }
          .codes-section {
            display: flex;
            flex-direction: column;
            gap: 1rem;
          }
          .section-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
          }
          .section-title h3 {
            font-size: 1rem;
            font-weight: 600;
            color: white;
            margin: 0;
          }
          .refresh-btn {
            background: none;
            border: none;
            color: #64748b;
            cursor: pointer;
            padding: 4px;
            display: flex;
            border-radius: 4px;
          }
          .refresh-btn:hover {
            color: white;
            background: rgba(255, 255, 255, 0.05);
          }
          .spinning {
            animation: spin 1s linear infinite;
          }
          @keyframes spin {
            to { rotate: 360deg; }
          }
          .table-wrapper {
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.01);
            overflow-x: auto;
            max-height: 350px;
          }
          .list-loading, .list-empty {
            padding: 3rem;
            text-align: center;
            color: #64748b;
            font-size: 0.9rem;
          }
          .codes-table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.88rem;
          }
          .codes-table th, .codes-table td {
            padding: 0.85rem 1.25rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          }
          .codes-table th {
            background: rgba(255, 255, 255, 0.02);
            font-weight: 500;
            color: #64748b;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
          }
          .code-cell {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #06b6d4;
          }
          .codes-table code {
            font-family: monospace;
            font-size: 0.9rem;
            letter-spacing: 0.02em;
          }
          .role-badge {
            display: inline-block;
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 6px;
            font-weight: 500;
          }
          .role-admin { background: rgba(168, 85, 247, 0.12); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.2); }
          .role-beta_user { background: rgba(14, 165, 233, 0.12); color: #38bdf8; border: 1px solid rgba(14, 165, 233, 0.2); }
          .role-standard_user { background: rgba(148, 163, 184, 0.12); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.2); }
          
          .status-badge {
            display: inline-block;
            font-size: 0.75rem;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 500;
          }
          .status-active { background: rgba(16, 185, 129, 0.1); color: #34d399; }
          .status-revoked { background: rgba(239, 68, 68, 0.1); color: #f87171; }
          
          .inactive-row {
            opacity: 0.55;
          }
          
          .action-btn {
            background: none;
            border: none;
            cursor: pointer;
            padding: 2px;
            display: flex;
          }
          .toggle-icon {
            transition: color 0.2s;
          }
          .toggle-icon.active { color: #10b981; }
          .toggle-icon.revoked { color: #64748b; }
        `}</style>
      </div>
    </AnimatePresence>
  );
};
