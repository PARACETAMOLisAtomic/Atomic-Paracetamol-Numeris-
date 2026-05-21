import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Briefcase, Plus, Search, Trash2, TrendingUp } from 'lucide-react';
import {
  addManualHolding,
  deleteManualHolding,
  getManualPortfolio,
  searchMarkets,
  type Holding,
  type SearchResult,
} from '../lib/api';

const ManualPortfolio: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [portfolio, setPortfolio] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const fetchPortfolio = async () => {
    try {
      const data = await getManualPortfolio();
      setPortfolio(data.holdings || []);
      setMessage('');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Sign in to manage your private portfolio.');
    }
  };

  useEffect(() => {
    let cancelled = false;
    getManualPortfolio()
      .then((data) => {
        if (!cancelled) {
          setPortfolio(data.holdings || []);
          setMessage('');
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setMessage(err instanceof Error ? err.message : 'Sign in to manage your private portfolio.');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSearch = async (value: string) => {
    setQuery(value);
    if (value.trim().length < 2) {
      setResults([]);
      return;
    }

    setLoading(true);
    try {
      const data = await searchMarkets(value);
      setResults(data.results || []);
      setMessage('');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const addStock = async (symbol: string) => {
    try {
      await addManualHolding(symbol, 1, 1000);
      await fetchPortfolio();
      setQuery('');
      setResults([]);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to add stock');
    }
  };

  const removeStock = async (symbol: string) => {
    try {
      await deleteManualHolding(symbol);
      await fetchPortfolio();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to remove stock');
    }
  };

  return (
    <section className="manual-portfolio-section" id="portfolio">
      <div className="section-kicker">
        <Briefcase size={16} /> Private Portfolio
      </div>
      <div className="portfolio-layout">
        <div className="portfolio-controls">
          <h2>Manage Your Assets</h2>
          <p>Search and add stocks manually to your private tracking engine.</p>
          {message && <div className="portfolio-message">{message}</div>}

          <div className="search-box">
            <Search className="search-icon" size={20} />
            <input
              type="text"
              placeholder="Search symbol (e.g. RELIANCE, AAPL)..."
              value={query}
              onChange={(event) => handleSearch(event.target.value)}
            />
            {loading && <div className="loader-small" />}
          </div>

          <AnimatePresence>
            {results.length > 0 && (
              <motion.div
                className="search-results"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                {results.map((item) => (
                  <div className="result-item" key={item.symbol}>
                    <div>
                      <strong>{item.symbol}</strong>
                      <span>{item.name}</span>
                    </div>
                    <button type="button" onClick={() => addStock(item.symbol)}>
                      <Plus size={16} /> Add
                    </button>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="portfolio-list">
          {portfolio.length === 0 ? (
            <div className="empty-portfolio">
              <p>No stocks added yet. Use the search box to build your portfolio.</p>
            </div>
          ) : (
            <div className="holdings-grid">
              {portfolio.map((stock) => (
                <motion.div
                  className="holding-card"
                  key={stock.symbol}
                  layout
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                >
                  <div className="card-top">
                    <h3>{stock.symbol}</h3>
                    <button type="button" onClick={() => removeStock(stock.symbol)} className="btn-delete" aria-label={`Remove ${stock.symbol}`}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div className="card-stats">
                    <div className="stat">
                      <span>Quantity</span>
                      <strong>{stock.quantity}</strong>
                    </div>
                    <div className="stat">
                      <span>Avg Price</span>
                      <strong>INR {stock.avg_price}</strong>
                    </div>
                  </div>
                  <div className="card-indicator">
                    <TrendingUp size={14} />
                    <span>Live Tracking Enabled</span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>

      <style>{`
        .manual-portfolio-section {
          padding: 4rem 2rem;
          background: rgba(15, 23, 42, 0.5);
          backdrop-filter: blur(12px);
          border-top: 1px solid rgba(255, 255, 255, 0.05);
        }
        .portfolio-layout {
          display: grid;
          grid-template-columns: 1fr 2fr;
          gap: 3rem;
          margin-top: 2rem;
        }
        .portfolio-message {
          margin-top: 1rem;
          padding: 0.75rem 0.9rem;
          border: 1px solid rgba(103, 232, 249, 0.22);
          border-radius: 10px;
          color: #bae6fd;
          background: rgba(14, 165, 233, 0.08);
          line-height: 1.45;
        }
        .search-box {
          position: relative;
          display: flex;
          align-items: center;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 0.75rem 1rem;
          margin-top: 1.5rem;
        }
        .search-box input {
          background: none;
          border: none;
          color: white;
          width: 100%;
          margin-left: 0.75rem;
          outline: none;
          font-size: 1rem;
        }
        .search-results {
          background: rgba(30, 41, 59, 0.95);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          margin-top: 0.5rem;
          max-height: 250px;
          overflow-y: auto;
          position: absolute;
          width: min(360px, calc(100vw - 48px));
          z-index: 50;
          box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }
        .result-item {
          padding: 0.75rem 1rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 1rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .result-item:hover {
          background: rgba(255, 255, 255, 0.05);
        }
        .result-item strong { display: block; color: #06b6d4; }
        .result-item span { font-size: 0.8rem; color: #94a3b8; }
        .result-item button {
          background: #06b6d4;
          color: white;
          border: none;
          padding: 0.4rem 0.8rem;
          border-radius: 6px;
          font-size: 0.8rem;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .holdings-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
          gap: 1.5rem;
        }
        .holding-card {
          background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          padding: 1.25rem;
          position: relative;
          overflow: hidden;
        }
        .card-top {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }
        .card-top h3 { margin: 0; color: white; letter-spacing: 1px; }
        .btn-delete {
          background: none;
          border: none;
          color: #ef4444;
          cursor: pointer;
          opacity: 0.65;
          transition: opacity 0.2s;
        }
        .btn-delete:hover { opacity: 1; }
        .card-stats {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
          margin-bottom: 1rem;
        }
        .stat span { display: block; font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; }
        .stat strong { font-size: 1.1rem; color: #f8fafc; }
        .card-indicator {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.75rem;
          color: #10b981;
          background: rgba(16, 185, 129, 0.1);
          padding: 0.4rem 0.8rem;
          border-radius: 20px;
          width: fit-content;
        }
        .empty-portfolio {
          min-height: 220px;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 2px dashed rgba(255, 255, 255, 0.08);
          border-radius: 20px;
          color: #94a3b8;
          text-align: center;
          padding: 1rem;
        }
        @media (max-width: 900px) {
          .portfolio-layout {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </section>
  );
};

export default ManualPortfolio;
