@echo off
echo Setting up Numeris...
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
cd frontend
call npm install
cd ..
mkdir data_cache\chroma 2>nul
mkdir data_cache\parquet 2>nul
mkdir data_cache\analyses 2>nul
mkdir models 2>nul
echo Setup complete. Configure .env and Vercel environment variables before production deploy.
