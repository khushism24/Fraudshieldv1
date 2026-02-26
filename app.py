"""
app.py
FraudShield AI — Streamlit Dashboard
Real-time fraud monitoring + RAG-powered AI assistant
"""
import os
import time
import glob
import json
import requests
import pandas as pd
import streamlit as st
from openai import OpenAI

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FraudShield AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
RAG_SERVER_URL = os.environ.get("RAG_SERVER_URL", "http://localhost:8765")
FRAUD_RULES_PATH = "./data/policies/fraud_rules.md"

# ── Helper: load latest data ────────────────────────────────────────────
@st.cache_data(ttl=2)
def load_transactions():
    """Load all transactions from Pathway output directory."""
    files = glob.glob("./data/output/all_transactions*.csv")
    if not files:
        return pd.DataFrame()
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception:
            pass
    if not dfs:
        return pd.DataFrame()
    combined = pd.concat(dfs, ignore_index=True)
    if "transaction_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["transaction_id"])
    return combined


@st.cache_data(ttl=2)
def load_fraud_alerts():
    """Load fraud-only alerts from Pathway output."""
    files = glob.glob("./data/output/fraud_alerts*.csv")
    if not files:
        return pd.DataFrame()
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception:
            pass
    if not dfs:
        return pd.DataFrame()
    combined = pd.concat(dfs, ignore_index=True)
    if "transaction_id" in combined.columns:
        combined = combined.drop_duplicates(subset=["transaction_id"])
    return combined


def load_policy_text():
    """Load fraud rules text for fallback RAG context."""
    try:
        with open(FRAUD_RULES_PATH, "r") as f:
            return f.read()
    except Exception:
        return "Fraud policy document not found."


def query_rag_server(question: str, num_results: int = 5) -> str:
    """Query Pathway's Document Store server for relevant policy chunks."""
    try:
        response = requests.post(
            f"{RAG_SERVER_URL}/v1/retrieve",
            json={"query": question, "k": num_results},
            timeout=5,
        )
        if response.status_code == 200:
            results = response.json()
            chunks = [r.get("text", "") for r in results if r.get("text")]
            return "\n\n---\n\n".join(chunks)
    except Exception:
        pass
    # Fallback: return full policy text
    return load_policy_text()


def ask_ai(question: str, transactions_context: str, policy_context: str) -> str:
    """Send question to OpenAI with fraud policy + transaction context (RAG)."""
    if not OPENAI_API_KEY:
        return "⚠️ OpenAI API key not set. Please set OPENAI_API_KEY in your .env file."

    client = OpenAI(api_key=OPENAI_API_KEY)

    system_prompt = f"""You are FraudShield AI, an expert fraud analyst assistant for a banking system.
You help analysts understand why transactions were flagged and what actions to take.

=== FRAUD DETECTION POLICIES (from live knowledge base) ===
{policy_context}

=== RECENT FLAGGED TRANSACTIONS (from real-time pipeline) ===
{transactions_context}

Answer questions clearly and concisely. Reference specific transactions by ID when relevant.
Cite the specific policy rule that applies. Always recommend a clear action."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        max_tokens=500,
        temperature=0.3,
    )
    return response.choices[0].message.content


# ── Custom CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 20px 30px;
        border-radius: 12px;
        margin-bottom: 20px;
        color: white;
    }
    .metric-card {
        background: #1e1e2e;
        border-radius: 10px;
        padding: 15px;
        border-left: 4px solid #e94560;
    }
    .critical-badge { background: #e94560; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    .high-badge { background: #ff6b35; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    .medium-badge { background: #f7c59f; color: black; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    .clean-badge { background: #27ae60; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
    .ai-response { background: #1a1a2e; border-left: 4px solid #4ecdc4; padding: 15px; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🛡️ FraudShield AI</h1>
    <p style="opacity:0.8; margin:0;">Real-Time Fraud Detection & RAG-Powered Intelligence | Powered by Pathway + OpenAI</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ System Status")
    
    # Check RAG server
    try:
        r = requests.get(f"{RAG_SERVER_URL}/v1/statistics", timeout=2)
        if r.status_code == 200:
            st.success("🟢 RAG Server: Online")
            stats = r.json()
            st.caption(f"Documents indexed: {stats.get('num_documents', 'N/A')}")
        else:
            st.warning("🟡 RAG Server: Degraded")
    except Exception:
        st.warning("🟡 RAG Server: Starting up...")

    # Pipeline status
    all_files = glob.glob("./data/output/*.csv")
    txn_files = glob.glob("./data/transactions/*.csv")
    if txn_files:
        st.success("🟢 Pathway Pipeline: Running")
        st.caption(f"Batches processed: {len(txn_files)}")
    else:
        st.info("⏳ Waiting for data stream...")

    st.divider()
    
    auto_refresh = st.toggle("Auto-refresh (2s)", value=True)
    if st.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("**Fraud Rules Active:**")
    st.caption("• Amount > $5,000 → HIGH")
    st.caption("• Hours 00:00–06:00 → MEDIUM")
    st.caption("• Both → CRITICAL")
    st.caption("• High-risk merchant → +25 pts")


# ── Main dashboard tabs ────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Live Dashboard", "🚨 Fraud Alerts", "🤖 AI Assistant"])

# ── TAB 1: LIVE DASHBOARD ────────────────────────────────────────────────
with tab1:
    df_all = load_transactions()

    if df_all.empty:
        st.info("⏳ Waiting for Pathway pipeline to process transactions... Make sure `generate_data.py` and `fraud_pipeline.py` are running.")
    else:
        # Metrics row
        total = len(df_all)
        flagged = df_all[df_all["is_fraud_flag"] == True] if "is_fraud_flag" in df_all.columns else pd.DataFrame()
        critical = df_all[df_all["risk_level"] == "CRITICAL"] if "risk_level" in df_all.columns else pd.DataFrame()
        clean = df_all[df_all["is_fraud_flag"] == False] if "is_fraud_flag" in df_all.columns else df_all

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Transactions", total, delta=f"+{min(total, 8)} latest batch")
        col2.metric("🚨 Flagged", len(flagged), delta=f"{len(flagged)/max(total,1)*100:.1f}% rate", delta_color="inverse")
        col3.metric("🔴 Critical", len(critical), delta_color="inverse")
        col4.metric("✅ Clean", len(clean))

        # Risk distribution chart
        if "risk_level" in df_all.columns:
            st.subheader("Risk Level Distribution")
            risk_counts = df_all["risk_level"].value_counts()
            col_chart, col_table = st.columns([1, 2])
            with col_chart:
                st.bar_chart(risk_counts)
            with col_table:
                st.dataframe(
                    df_all[["transaction_id", "amount", "user_id", "merchant", 
                             "hour", "risk_score", "risk_level", "fraud_reason"]]
                    .sort_values("risk_score", ascending=False)
                    .head(20),
                    use_container_width=True,
                    hide_index=True,
                )


# ── TAB 2: FRAUD ALERTS ────────────────────────────────────────────────
with tab2:
    df_fraud = load_fraud_alerts()

    if df_fraud.empty:
        st.info("✅ No fraud alerts yet — or pipeline is still starting. Check back shortly.")
    else:
        st.subheader(f"🚨 {len(df_fraud)} Active Fraud Alerts")

        # Critical alerts at top
        if "risk_level" in df_fraud.columns:
            critical_alerts = df_fraud[df_fraud["risk_level"] == "CRITICAL"]
            if not critical_alerts.empty:
                st.error(f"🔴 {len(critical_alerts)} CRITICAL alerts require immediate action!")
                for _, row in critical_alerts.head(5).iterrows():
                    with st.expander(f"🔴 CRITICAL — {row.get('transaction_id','?')} | ${row.get('amount',0):,.2f} | {row.get('merchant','?')}"):
                        col_a, col_b = st.columns(2)
                        col_a.write(f"**User:** {row.get('user_id','?')}")
                        col_a.write(f"**Location:** {row.get('location','?')}")
                        col_a.write(f"**Card Type:** {row.get('card_type','?')}")
                        col_b.write(f"**Risk Score:** {row.get('risk_score','?')}/100")
                        col_b.write(f"**Hour:** {row.get('hour','?')}:00")
                        st.warning(f"**Reason:** {row.get('fraud_reason','?')}")

        st.dataframe(
            df_fraud[["transaction_id", "amount", "user_id", "merchant", 
                      "hour", "location", "risk_score", "risk_level", "fraud_reason"]]
            .sort_values("risk_score", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


# ── TAB 3: AI ASSISTANT ─────────────────────────────────────────────────
with tab3:
    st.subheader("🤖 FraudShield AI Assistant")
    st.caption("Ask anything about flagged transactions or fraud policies. Powered by Pathway RAG + OpenAI GPT-4o mini.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Suggested questions
    if not st.session_state.chat_history:
        st.write("**💡 Try asking:**")
        suggestions = [
            "Why are off-hours transactions flagged?",
            "What should I do with a CRITICAL risk transaction?",
            "Explain the combo fraud rule",
            "What is the escalation process for high-risk merchants?",
        ]
        cols = st.columns(2)
        for i, s in enumerate(suggestions):
            if cols[i % 2].button(s, key=f"suggest_{i}"):
                st.session_state.chat_history.append({"role": "user", "content": s})
                st.rerun()

    # Chat input
    user_input = st.chat_input("Ask about fraud policies or specific transactions...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.rerun()

    # Generate AI response for last unanswered message
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        last_question = st.session_state.chat_history[-1]["content"]
        with st.chat_message("assistant"):
            with st.spinner("Querying knowledge base & generating response..."):
                # 1. Retrieve relevant policy chunks from Pathway RAG server
                policy_context = query_rag_server(last_question)

                # 2. Get recent fraud alerts as context
                df_fraud = load_fraud_alerts()
                if not df_fraud.empty:
                    txn_context = df_fraud.head(10).to_string(index=False)
                else:
                    txn_context = "No fraud alerts detected yet."

                # 3. Ask OpenAI
                answer = ask_ai(last_question, txn_context, policy_context)
                st.write(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})


# ── Auto-refresh ────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(2)
    st.cache_data.clear()
    st.rerun()
