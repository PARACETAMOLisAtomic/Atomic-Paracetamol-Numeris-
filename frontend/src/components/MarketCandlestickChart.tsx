import { useEffect, useRef, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { getMarketCandles, type Candle } from '../lib/api';

type ChartStatus = 'loading' | 'ready' | 'error';

export default function MarketCandlestickChart({ symbol }: { symbol: string }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [status, setStatus] = useState<ChartStatus>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    let cancelled = false;

    getMarketCandles(symbol)
      .then((payload) => {
        if (cancelled) return;
        setCandles(payload.candles);
        setStatus('ready');
        setMessage('');
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setStatus('error');
        setMessage(error instanceof Error ? error.message : 'Unable to load chart data');
      });

    return () => {
      cancelled = true;
    };
  }, [symbol]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !candles.length) return undefined;

    let resizeObserver: ResizeObserver | undefined;
    let disposed = false;
    let cleanup = () => {};

    import('lightweight-charts').then(({ createChart, ColorType }) => {
      if (disposed) return;

      const chart = createChart(container, {
        height: 420,
        layout: {
          background: { type: ColorType.Solid, color: 'transparent' },
          textColor: 'rgba(237, 247, 255, 0.72)',
          fontFamily: 'Inter, system-ui, sans-serif',
        },
        grid: {
          vertLines: { color: 'rgba(255, 255, 255, 0.055)' },
          horzLines: { color: 'rgba(255, 255, 255, 0.055)' },
        },
        rightPriceScale: {
          borderColor: 'rgba(255, 255, 255, 0.12)',
          scaleMargins: { top: 0.08, bottom: 0.24 },
        },
        timeScale: {
          borderColor: 'rgba(255, 255, 255, 0.12)',
          rightOffset: 8,
          barSpacing: 10,
        },
        crosshair: {
          mode: 1,
        },
      });

      const candleSeries = chart.addCandlestickSeries({
        upColor: '#19c37d',
        downColor: '#ef4444',
        wickUpColor: '#19c37d',
        wickDownColor: '#ef4444',
        borderVisible: false,
      });

      candleSeries.setData(
        candles.map((candle) => ({
          time: candle.time,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
        })),
      );

      const volumeSeries = chart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: '',
        color: 'rgba(103, 232, 249, 0.24)',
      });

      volumeSeries.setData(
        candles.map((candle) => ({
          time: candle.time,
          value: candle.volume,
          color: candle.close >= candle.open ? 'rgba(25, 195, 125, 0.28)' : 'rgba(239, 68, 68, 0.28)',
        })),
      );

      chart.priceScale('').applyOptions({
        scaleMargins: { top: 0.78, bottom: 0 },
      });
      chart.timeScale().fitContent();

      resizeObserver = new ResizeObserver(([entry]) => {
        chart.applyOptions({ width: Math.floor(entry.contentRect.width) });
      });
      resizeObserver.observe(container);

      cleanup = () => {
        resizeObserver?.disconnect();
        chart.remove();
      };
    });

    return () => {
      disposed = true;
      cleanup();
    };
  }, [candles]);

  return (
    <div className="tradingview-panel">
      <div className="tradingview-header">
        <div>
          <span>Live market structure</span>
          <strong>{symbol}</strong>
        </div>
        <div className={`chart-status chart-status-${status}`}>
          {status === 'loading' && <RefreshCw size={14} />}
          {status === 'ready' ? `${candles.length} candles` : status}
        </div>
      </div>
      {status === 'error' && <div className="chart-error">{message}</div>}
      <div ref={containerRef} className="candlestick-chart" aria-label={`${symbol} candlestick chart`} />
    </div>
  );
}
