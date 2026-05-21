import os
from tqdm import tqdm
import yfinance as yf
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Hardcoded lists
NIFTY50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "BAJFINANCE.NS",
    "HCLTECH.NS", "ASIANPAINT.NS", "AXISBANK.NS", "KOTAKBANK.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS", "BAJAJFINSV.NS",
    "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS", "M&M.NS", "ONGC.NS",
    "TATASTEEL.NS", "HINDUNILVR.NS", "COALINDIA.NS", "JSWSTEEL.NS", "TATAMOTORS.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "GRASIM.NS", "HINDALCO.NS", "TECHM.NS",
    "CIPLA.NS", "DRREDDY.NS", "EICHERMOT.NS", "DIVISLAB.NS", "APOLLOHOSP.NS",
    "BRITANNIA.NS", "BAJAJ-AUTO.NS", "INDUSINDBK.NS", "HEROMOTOCO.NS", "SBILIFE.NS",
    "TATACONSUM.NS", "UPL.NS", "LTIM.NS", "BPCL.NS", "BAJAJ-AUTO.NS"
]

SP500_TOP100 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "LLY", "V",
    "UNH", "XOM", "JPM", "JNJ", "AVGO", "WMT", "MA", "PG", "HD", "CVX",
    "MRK", "ORCL", "ABBV", "COST", "PEP", "BAC", "KO", "TMO", "MCD", "CSCO",
    "ACN", "CRM", "NFLX", "LIN", "AMD", "ABT", "DHR", "CMCSA", "TXN", "WFC",
    "INTC", "PM", "COP", "QCOM", "VZ", "NEE", "INTU", "CAT", "BA", "IBM",
    "AMGN", "UNP", "SPGI", "GE", "HON", "NOW", "ISRG", "PFE", "RTX", "LOW",
    "SYK", "GS", "ELV", "T", "BKNG", "PLD", "MDT", "TJX", "MS", "PGR",
    "LMT", "VRTX", "ADI", "C", "SBUX", "BMY", "MDLZ", "CB", "MMC", "GILD",
    "ADP", "DE", "REGN", "CI", "LRCX", "AMAT", "CVS", "BSX", "ZTS", "MO",
    "FI", "KLAC", "DUK", "PANW", "SNPS", "CSX", "SO", "CDNS", "BDX", "SHW"
]

PARQUET_DIR = "./data_cache/parquet"

def get_parquet_path(symbol: str) -> str:
    return os.path.join(PARQUET_DIR, f"{symbol}.parquet")

def fetch_and_save(symbol: str) -> bool:
    try:
        df = yf.download(symbol, period="5y", interval="1d", progress=False)
        if df.empty:
            return False
            
        # Flatten multi-index columns if present (yfinance sometimes returns multi-index)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip() for col in df.columns.values]
            
        # Convert index to a column to save correctly
        df.reset_index(inplace=True)
        
        # Ensure all column names are strings
        df.columns = df.columns.astype(str)
        
        table = pa.Table.from_pandas(df)
        pq.write_table(table, get_parquet_path(symbol), compression='zstd')
        return True
    except Exception as e:
        return False

def get_dir_size(path='.'):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

def warmup():
    os.makedirs(PARQUET_DIR, exist_ok=True)
    all_symbols = NIFTY50 + SP500_TOP100
    
    print(f"Warming up cache for {len(all_symbols)} symbols...")
    
    downloaded = 0
    skipped = 0
    failed_symbols = []
    
    for sym in tqdm(all_symbols):
        if os.path.exists(get_parquet_path(sym)):
            skipped += 1
            continue
            
        success = fetch_and_save(sym)
        if success:
            downloaded += 1
        else:
            failed_symbols.append(sym)
            
    if failed_symbols:
        with open("failed_symbols.txt", "w") as f:
            for s in failed_symbols:
                f.write(f"{s}\n")
                
    total_size_mb = get_dir_size(PARQUET_DIR) / (1024 * 1024)
    
    print(f"\nSummary:")
    print(f"- Downloaded: {downloaded}")
    print(f"- Skipped (already cached): {skipped}")
    print(f"- Failed: {len(failed_symbols)}")
    if failed_symbols:
        print(f"  See failed_symbols.txt for details.")
    print(f"Total cache size: {total_size_mb:.2f} MB")

if __name__ == "__main__":
    warmup()
