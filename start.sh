#!/bin/bash
# start.sh — Railway entrypoint
# Starts all 3 background services then launches Streamlit

echo "[Start] Creating data directories..."
mkdir -p data/transactions data/output data/policies

echo "[Start] Starting data generator..."
python generate_data.py &

echo "[Start] Starting Pathway fraud pipeline..."
python fraud_pipeline.py &

echo "[Start] Starting Pathway RAG server..."
python rag_server.py &

# Give pipeline a few seconds to initialize before dashboard starts
sleep 5

echo "[Start] Starting Streamlit dashboard..."
streamlit run app.py --server.port ${PORT:-8501} --server.address 0.0.0.0
