# 🛡️ FraudShield AI
### Real-Time Fraud Detection with RAG-Powered Intelligence
**Built for Hack For Green Bharat — Pathway Track**

---

## 🏗️ Architecture

```
┌─────────────────┐     CSV files      ┌──────────────────────┐     ┌──────────────────┐
│  generate_data  │ ─────────────────► │   fraud_pipeline.py  │ ──► │  data/output/    │
│  (Simulator)    │                    │   (Pathway Stream)   │     │  CSV results     │
└─────────────────┘                    └──────────────────────┘     └────────┬─────────┘
                                                                              │
┌─────────────────┐     REST API       ┌──────────────────────┐              │
│  data/policies/ │ ─────────────────► │    rag_server.py     │◄─────────────┘
│  (Fraud Rules)  │                    │  (Pathway Doc Store) │
└─────────────────┘                    └──────────┬───────────┘
                                                   │ /v1/retrieve
                                        ┌──────────▼───────────┐     ┌─────────────┐
                                        │      app.py          │ ──► │  OpenAI     │
                                        │   (Streamlit UI)     │     │  GPT-4o mini│
                                        └──────────────────────┘     └─────────────┘
                                               ↑
                                        http://localhost:8501
```

### How it satisfies Pathway requirements:
| Requirement | Implementation |
|---|---|
| ✅ Live data ingestion | `pw.io.csv.read()` in streaming mode watches directory |
| ✅ Streaming transformations | `pw.apply()`, `.filter()`, `.select()` on live tables |
| ✅ Real-time feature engineering | Risk score & fraud reason computed per transaction |
| ✅ LLM xPack / Document Store | `pathway.xpacks.llm.document_store.DocumentStore` |
| ✅ RAG pipeline | Policies indexed → semantic search → OpenAI answer |
| ✅ Docker deployment | Full `docker-compose.yml` |

---

## 🚀 Quick Start (3 options)

### Option A: Docker Compose (Recommended — one command!)

```bash
# 1. Clone / unzip the project
cd fraudshield

# 2. Set your API key
cp .env.example .env
# Edit .env and add your OpenAI API key

# 3. Launch everything
docker compose up --build

# 4. Open dashboard
open http://localhost:8501
```

---

### Option B: Run locally (without Docker)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
export OPENAI_API_KEY="sk-your-key-here"

# Open 4 terminal windows and run one command in each:

# Terminal 1 — Generate streaming data
python generate_data.py

# Terminal 2 — Pathway fraud detection pipeline
python fraud_pipeline.py

# Terminal 3 — Pathway RAG server
python rag_server.py

# Terminal 4 — Streamlit dashboard
streamlit run app.py
```

Then open **http://localhost:8501** 🎉

---

### Option C: Demo mode (no Docker needed, just the dashboard)

If you want to show a quick demo without running all services:
```bash
pip install -r requirements.txt
export OPENAI_API_KEY="sk-your-key-here"
# Run generator and pipeline in background
python generate_data.py &
python fraud_pipeline.py &
streamlit run app.py
```

---

## 📁 Project Structure

```
fraudshield/
├── generate_data.py          # Simulates real-time bank transactions (Pathway demo module alternative)
├── fraud_pipeline.py         # 🔑 Main Pathway streaming pipeline — fraud detection rules
├── rag_server.py             # 🔑 Pathway Document Store — live-indexes fraud policies
├── app.py                    # Streamlit dashboard + AI chat interface
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container definition
├── docker-compose.yml        # Orchestrates all 4 services
├── .env.example              # API key template
└── data/
    ├── transactions/         # Streaming input (written by generator, read by Pathway)
    ├── output/               # Pathway output (all_transactions.csv, fraud_alerts.csv)
    └── policies/
        └── fraud_rules.md    # Knowledge base for RAG
```

---

## 🎯 Features

### Real-Time Fraud Detection (Pathway Pipeline)
- **Rule 1:** Amount > $5,000 → +40 risk points
- **Rule 2:** Transaction between 00:00–06:00 → +30 risk points  
- **Rule 3:** High value + off-hours combo → +20 bonus (CRITICAL)
- **Rule 4:** High-risk merchant (crypto, wire transfer) → +25 points
- Risk levels: CLEAN → LOW → MEDIUM → HIGH → CRITICAL

### RAG-Powered AI Assistant (Pathway + OpenAI)
- Ask natural language questions about fraud policies
- Get explanations for specific flagged transactions
- Pathway's Document Store serves semantically relevant policy chunks
- OpenAI generates context-aware responses

### Live Dashboard (Streamlit)
- Auto-refreshing metrics (every 2 seconds)
- Risk distribution charts
- Drill-down fraud alert cards
- Full transaction table with risk scores

---

## 💡 Example Questions for the AI Assistant

- *"Why are off-hours transactions considered suspicious?"*
- *"What action should I take for a CRITICAL risk transaction?"*
- *"Explain the combo fraud rule and when it triggers"*
- *"What are the AML compliance requirements?"*
- *"Which merchants are considered high-risk and why?"*

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Streaming Engine | **Pathway** (Python) |
| RAG / Document Store | **Pathway xPacks LLM** |
| LLM | **OpenAI GPT-4o mini** |
| Embeddings | **OpenAI text-embedding-3-small** |
| Dashboard | **Streamlit** |
| Containerization | **Docker / Docker Compose** |

---

## 📈 Extending This Project

- **Add Kafka**: Replace CSV connector with `pw.io.kafka.read()` for production-grade ingestion
- **Add more rules**: Extend `compute_risk_score()` in `fraud_pipeline.py`
- **Add more documents**: Drop any PDF/markdown into `data/policies/` — RAG server auto-indexes!
- **Real transaction data**: Connect to a payment gateway API via Pathway's HTTP connector
- **Alerting**: Add `pw.io.http.write()` to push alerts to Slack/PagerDuty

---

*Built with ❤️ for Hack For Green Bharat — Pathway Track*
