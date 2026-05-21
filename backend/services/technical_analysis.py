import pandas as pd
import numpy as np
import pandas_ta as ta
from scipy.signal import argrelextrema
from typing import Dict, Any, List
import traceback
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class InsufficientDataError(Exception):
    pass

class TechnicalAnalyzer:
    def __init__(self):
        pass

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < 50:
            raise InsufficientDataError(f"Data length {len(df)} is less than required 50.")
        
        # calculate indicators
        df = self._calculate_trend(df)
        df = self._calculate_momentum(df)
        df = self._calculate_volume(df)
        df = self._calculate_vwap(df)
        
        patterns = self._detect_candlestick_patterns(df)
        chart_patterns = self._detect_chart_patterns(df)
        fib_levels = self._calculate_fibonacci_levels(df)
        
        signal_score, signal_type = self._calculate_signal_score(df, patterns)
        
        return {
            "trend": "Bullish" if df['SMA_20'].iloc[-1] > df['SMA_50'].iloc[-1] else "Bearish",
            "momentum": {"RSI": float(df['RSI'].iloc[-1]), "MACD": float(df['MACD'].iloc[-1])},
            "volume_trend": "Increasing" if df['Volume'].iloc[-1] > df['Volume'].rolling(10).mean().iloc[-1] else "Decreasing",
            "patterns": patterns[-5:], # last 5 days
            "chart_patterns": chart_patterns,
            "fibonacci_levels": fib_levels,
            "signal_score": signal_score,
            "signal_type": signal_type,
            "latest_data": df.iloc[-1].to_dict()
        }

    def _calculate_trend(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            df['SMA_20'] = ta.sma(df['Close'], length=20)
            df['SMA_50'] = ta.sma(df['Close'], length=50)
            df['SMA_200'] = ta.sma(df['Close'], length=200)
            df['EMA_9'] = ta.ema(df['Close'], length=9)
            df['EMA_21'] = ta.ema(df['Close'], length=21)
        except Exception as e:
            logger.error(f"Error calculating trend indicators: {e}")
        return df

    def _calculate_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            df['RSI'] = ta.rsi(df['Close'], length=14)
            macd = ta.macd(df['Close'])
            if macd is not None and not macd.empty:
                df['MACD'] = macd.iloc[:, 0]
                df['MACD_Signal'] = macd.iloc[:, 1]
                df['MACD_Hist'] = macd.iloc[:, 2]
            else:
                df['MACD'] = df['MACD_Signal'] = df['MACD_Hist'] = np.nan
        except Exception as e:
            logger.error(f"Error calculating momentum indicators: {e}")
        return df

    def _calculate_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            df['OBV'] = ta.obv(df['Close'], df['Volume'])
            df['Volume_SMA'] = ta.sma(df['Volume'], length=20)
        except Exception as e:
            logger.error(f"Error calculating volume indicators: {e}")
        return df

    def _calculate_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            df['Date'] = df.index.date
            df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
            df['TP_V'] = df['Typical_Price'] * df['Volume']
            df['Cum_TP_V'] = df.groupby('Date')['TP_V'].cumsum()
            df['Cum_V'] = df.groupby('Date')['Volume'].cumsum()
            df['VWAP'] = df['Cum_TP_V'] / df['Cum_V']
            df.drop(['Date', 'Typical_Price', 'TP_V', 'Cum_TP_V', 'Cum_V'], axis=1, inplace=True)
        except Exception as e:
            logger.error(f"Error calculating VWAP: {e}")
        return df

    def _detect_candlestick_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        patterns_found = []
        try:
            for i in range(1, len(df)):
                row = df.iloc[i]
                prev_row = df.iloc[i-1]
                
                open_p, high_p, low_p, close_p = row['Open'], row['High'], row['Low'], row['Close']
                p_open, p_high, p_low, p_close = prev_row['Open'], prev_row['High'], prev_row['Low'], prev_row['Close']
                
                body = abs(open_p - close_p)
                p_body = abs(p_open - p_close)
                range_p = high_p - low_p
                
                if range_p == 0:
                    continue
                    
                upper_shadow = high_p - max(open_p, close_p)
                lower_shadow = min(open_p, close_p) - low_p
                
                if body / range_p < 0.1:
                    patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Doji"})
                
                if lower_shadow > 2 * body and upper_shadow < 0.3 * body and p_close < p_open:
                    patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Hammer"})
                    
                if body > p_body and close_p > p_open and open_p < p_close and p_close < p_open and close_p > open_p:
                    patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Engulfing Bullish"})
                    
                if body > p_body and close_p < p_open and open_p > p_close and p_close > p_open and close_p < open_p:
                    patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Engulfing Bearish"})
                    
                if i > 2:
                    pp_row = df.iloc[i-2]
                    if pp_row['Close'] < pp_row['Open'] and body / range_p < 0.3 and close_p > open_p and close_p > (pp_row['Open'] + pp_row['Close'])/2:
                        patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Morning Star"})
                        
                if i > 2:
                    pp_row = df.iloc[i-2]
                    if pp_row['Close'] > pp_row['Open'] and body / range_p < 0.3 and close_p < open_p and close_p < (pp_row['Open'] + pp_row['Close'])/2:
                        patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Evening Star"})
                        
                if upper_shadow > 2 * body and lower_shadow < 0.3 * body and p_close > p_open:
                    patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Shooting Star"})
                    
                if upper_shadow > 2 * body and lower_shadow < 0.3 * body and p_close < p_open:
                    patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Inverted Hammer"})
                    
                if p_close < p_open and close_p > open_p and open_p < p_low and close_p > (p_open + p_close)/2:
                    patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Piercing Line"})
                    
                if p_close > p_open and close_p < open_p and open_p > p_high and close_p < (p_open + p_close)/2:
                    patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Dark Cloud Cover"})
                    
                if lower_shadow > 2 * body and upper_shadow < 0.3 * body and p_close > p_open:
                    patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Hanging Man"})
                    
                if p_close < p_open and close_p > open_p and open_p > p_close and close_p < p_open and body < p_body * 0.5:
                    patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Bullish Harami"})
                    
                if p_close > p_open and close_p < open_p and open_p < p_close and close_p > p_open and body < p_body * 0.5:
                    patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Bearish Harami"})
                    
                if upper_shadow < 0.05 * body and lower_shadow < 0.05 * body and body > range_p * 0.9:
                    patterns_found.append({"date": df.index[i].isoformat(), "pattern": "Marubozu"})
                    
        except Exception as e:
            logger.error(f"Error detecting candlestick patterns: {e}")
        return patterns_found

    def _detect_chart_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        patterns = []
        try:
            close_prices = df['Close'].values
            
            local_max = argrelextrema(close_prices, np.greater, order=5)[0]
            local_min = argrelextrema(close_prices, np.less, order=5)[0]
            
            if len(local_max) >= 3 and len(local_min) >= 2:
                p1, p2, p3 = close_prices[local_max[-3:]]
                if p1 < p2 and p3 < p2 and abs(p1 - p3) / p1 < 0.05:
                    patterns.append({"pattern": "Head and Shoulders", "confidence": 0.8})
                    
            if len(local_max) >= 2 and len(local_min) >= 2:
                p1, p2 = close_prices[local_max[-2:]]
                if abs(p1 - p2) / p1 < 0.03:
                    patterns.append({"pattern": "Double Top", "confidence": 0.7})
                    
                p1, p2 = close_prices[local_min[-2:]]
                if abs(p1 - p2) / p1 < 0.03:
                    patterns.append({"pattern": "Double Bottom", "confidence": 0.7})
                    
        except Exception as e:
            logger.error(f"Error detecting chart patterns: {e}")
        return patterns

    def _calculate_fibonacci_levels(self, df: pd.DataFrame) -> Dict[str, float]:
        levels = {}
        try:
            recent_df = df.tail(100)
            max_price = recent_df['High'].max()
            min_price = recent_df['Low'].min()
            diff = max_price - min_price
            
            levels = {
                "0.0%": float(max_price),
                "23.6%": float(max_price - 0.236 * diff),
                "38.2%": float(max_price - 0.382 * diff),
                "50.0%": float(max_price - 0.5 * diff),
                "61.8%": float(max_price - 0.618 * diff),
                "78.6%": float(max_price - 0.786 * diff),
                "100.0%": float(min_price)
            }
        except Exception as e:
            logger.error(f"Error calculating Fibonacci levels: {e}")
        return levels

    def _calculate_signal_score(self, df: pd.DataFrame, patterns: List[Dict[str, Any]]) -> tuple[float, str]:
        try:
            score = 0.0
            last = df.iloc[-1]
            
            # Trend 30%
            trend_score = 0
            if 'SMA_20' in df.columns and 'SMA_50' in df.columns and not np.isnan(last['SMA_20']) and not np.isnan(last['SMA_50']):
                if last['SMA_20'] > last['SMA_50']:
                    trend_score += 15
                if last['Close'] > last['SMA_20']:
                    trend_score += 15
            score += trend_score
            
            # Momentum 25%
            momentum_score = 0
            if 'RSI' in df.columns and not np.isnan(last['RSI']):
                if 30 <= last['RSI'] <= 70:
                    momentum_score += 12.5
                elif last['RSI'] < 30:
                    momentum_score += 25
            if 'MACD' in df.columns and 'MACD_Signal' in df.columns and not np.isnan(last['MACD']) and not np.isnan(last['MACD_Signal']):
                if last['MACD'] > last['MACD_Signal']:
                    momentum_score += 12.5
            score += momentum_score
            
            # Volume 25%
            volume_score = 0
            if 'Volume_SMA' in df.columns and not np.isnan(last['Volume_SMA']):
                if last['Volume'] > last['Volume_SMA']:
                    volume_score += 25
            score += volume_score
            
            # Pattern 20%
            pattern_score = 0
            recent_patterns = [p for p in patterns if p['date'] == df.index[-1].isoformat()]
            bullish_patterns = ["Hammer", "Engulfing Bullish", "Morning Star", "Piercing Line", "Bullish Harami"]
            bearish_patterns = ["Engulfing Bearish", "Evening Star", "Shooting Star", "Dark Cloud Cover", "Hanging Man", "Bearish Harami"]
            
            for p in recent_patterns:
                if p['pattern'] in bullish_patterns:
                    pattern_score += 20
                    break
                elif p['pattern'] in bearish_patterns:
                    pattern_score -= 20
                    break
            score += max(0, pattern_score)
            
            signal_type = "HOLD"
            if score >= 70:
                signal_type = "BUY"
            elif score <= 30:
                signal_type = "SELL"
                
            return min(100.0, max(0.0, score)), signal_type
        except Exception as e:
            logger.error(f"Error calculating signal score: {e}")
            return 50.0, "HOLD"

    def backtest_strategy(self, df: pd.DataFrame, strategy: str = "SMA_Crossover") -> Dict[str, Any]:
        initial_capital = 100000.0
        capital = initial_capital
        position = 0
        trades = []
        
        try:
            for i in range(1, len(df)):
                row = df.iloc[i]
                prev_row = df.iloc[i-1]
                
                if strategy == "SMA_Crossover":
                    if pd.isna(prev_row.get('SMA_20')) or pd.isna(prev_row.get('SMA_50')):
                        continue
                        
                    if prev_row['SMA_20'] < prev_row['SMA_50'] and row['SMA_20'] > row['SMA_50']:
                        if position == 0:
                            shares_to_buy = int(capital / row['Close'])
                            if shares_to_buy > 0:
                                capital -= shares_to_buy * row['Close']
                                position = shares_to_buy
                                trades.append({"date": df.index[i].isoformat(), "type": "BUY", "price": float(row['Close']), "shares": position})
                    
                    elif prev_row['SMA_20'] > prev_row['SMA_50'] and row['SMA_20'] < row['SMA_50']:
                        if position > 0:
                            capital += position * row['Close']
                            trades.append({"date": df.index[i].isoformat(), "type": "SELL", "price": float(row['Close']), "shares": position})
                            position = 0
                            
            final_value = capital + (position * df.iloc[-1]['Close'])
            returns = ((final_value - initial_capital) / initial_capital) * 100
            
            return {
                "initial_capital": initial_capital,
                "final_value": final_value,
                "returns_percent": returns,
                "total_trades": len(trades),
                "trade_log": trades
            }
        except Exception as e:
            logger.error(f"Error during backtesting: {e}")
            return {"error": str(e)}
