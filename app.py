"""
app.py — FraudShield AI Dashboard
Self-contained: generates + scores transactions in-memory if pipeline output not found
"""
import os, time, glob, random, uuid, json, requests
import pandas as pd
import streamlit as st
from datetime import datetime
from openai import OpenAI

st.set_page_config(page_title="FraudShield AI", page_icon="🛡️", layout="wide")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
RAG_SERVER_URL  = os.environ.get("RAG_SERVER_URL", "http://localhost:8765")

# ── In-memory transaction store ─────────────────────────────────────────
if "transactions" not in st.session_state:
    st.session_state.transactions = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_gen" not in st.session_state:
    st.session_state.last_gen = 0

MERCHANTS = [
    "Amazon","Flipkart","Swiggy","Zomato","BookMyShow",
    "BigBasket","Myntra","Uber","Netflix",
    "CryptoExchange_BuyBit","WireTransfer_Global","CasinoRoyal",
    "MedPlus Pharmacy","IRCTC","Reliance Mart","D-Mart",
]
HIGH_RISK = {"CryptoExchange_BuyBit","WireTransfer_Global","CasinoRoyal"}
USERS     = [f"USER_{i:04d}" for i in range(1,51)]
LOCATIONS = ["Mumbai","Delhi","Bangalore","Hyderabad","Chennai","Pune","Kolkata"]
CARDS     = ["Visa","Mastercard","RuPay","Amex"]

def score_transaction(amount, hour, merchant):
    score = 0
    reasons = []
    if amount > 5000:
        score += 40
        reasons.append(f"HIGH AMOUNT (₹{amount:,.0f} > ₹5000)")
    if hour < 6:
        score += 30
        reasons.append(f"OFF-HOURS ({hour:02d}:00)")
    if amount > 1000 and hour < 6:
        score += 20
        reasons.append("CRITICAL COMBO")
    if merchant in HIGH_RISK:
        score += 25
        reasons.append("HIGH-RISK MERCHANT")
    score = min(score, 100)
    if score >= 70: level = "CRITICAL"
    elif score >= 50: level = "HIGH"
    elif score >= 30: level = "MEDIUM"
    elif score > 0:  level = "LOW"
    else:            level = "CLEAN"
    return score, level, " | ".join(reasons) if reasons else "CLEAN"

def generate_batch():
    batch = []
    for _ in range(random.randint(3,7)):
        r = random.random()
        if r < 0.15:
            amount = round(random.uniform(5001,25000),2)
            hour   = random.randint(0,5)
        elif r < 0.28:
            amount = round(random.uniform(500,4999),2)
            hour   = random.randint(0,5)
        else:
            amount = round(random.uniform(50,4500),2)
            hour   = random.randint(6,23)
        merchant = random.choice(MERCHANTS)
        score, level, reason = score_transaction(amount, hour, merchant)
        batch.append({
            "transaction_id": str(uuid.uuid4())[:8].upper(),
            "amount": amount,
            "user_id": random.choice(USERS),
            "hour": hour,
            "merchant": merchant,
            "location": random.choice(LOCATIONS),
            "card_type": random.choice(CARDS),
            "risk_score": score,
            "risk_level": level,
            "fraud_reason": reason,
            "is_fraud_flag": score >= 30,
        })
    return batch

def load_from_pathway():
    """Try to load from Pathway pipeline output if running."""
    try:
        files = glob.glob("./data/output/all_transactions*.csv")
        if not files:
            return None
        dfs = [pd.read_csv(f) for f in files]
        df = pd.concat(dfs, ignore_index=True)
        if "transaction_id" in df.columns:
            df = df.drop_duplicates(subset=["transaction_id"])
        if len(df) > 0:
            return df
    except Exception:
        pass
    return None

def get_df():
    """Get transactions — from Pathway output or in-memory generated."""
    # Try Pathway first
    df = load_from_pathway()
    if df is not None:
        return df, True

    # Fall back to in-memory stream
    now = time.time()
    if now - st.session_state.last_gen > 2:
        new = generate_batch()
        st.session_state.transactions.extend(new)
        if len(st.session_state.transactions) > 500:
            st.session_state.transactions = st.session_state.transactions[-500:]
        st.session_state.last_gen = now

    if not st.session_state.transactions:
        return pd.DataFrame(), False
    return pd.DataFrame(st.session_state.transactions), False

def load_policy_text():
    paths = glob.glob("./data/policies/*.md") + glob.glob("./data/policies/*.txt")
    if paths:
        return "\n\n".join(open(p).read() for p in paths)
    return """
FraudShield AI Fraud Detection Rules:
Rule 1: Amount > $5000 → HIGH risk (+40 points). Block and notify user.
Rule 2: Transaction between 00:00-06:00 → MEDIUM risk (+30 points). Require 2FA.
Rule 3: High amount AND off-hours → CRITICAL (+20 bonus). Block card immediately.
Rule 4: High-risk merchants (crypto, wire transfer, gambling) → +25 points.
Risk Levels: CLEAN(0) LOW(1-29) MEDIUM(30-49) HIGH(50-69) CRITICAL(70+)
Escalation: LOW=log only, MEDIUM=alert user, HIGH=block txn, CRITICAL=block card+emergency contact.
"""

def query_rag(question):
    try:
        r = requests.post(f"{RAG_SERVER_URL}/v1/retrieve",
                          json={"query": question, "k": 4}, timeout=3)
        if r.status_code == 200:
            results = r.json()
            chunks = [x.get("text","") for x in results if x.get("text")]
            if chunks:
                return "\n\n---\n\n".join(chunks)
    except Exception:
        pass
    return load_policy_text()

def ask_ai(question, txn_context, policy_context):
    if not OPENAI_API_KEY:
        return "⚠️ OPENAI_API_KEY not set. Add it in Railway → Variables."
    client = OpenAI(api_key=OPENAI_API_KEY)
    system = f"""You are FraudShield AI, an expert fraud analyst for a banking system.

=== FRAUD POLICIES ===
{policy_context}

=== RECENT FLAGGED TRANSACTIONS ===
{txn_context}

Answer clearly. Reference transaction IDs and cite specific rules when relevant."""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":system},{"role":"user","content":question}],
        max_tokens=500, temperature=0.3
    )
    return resp.choices[0].message.content

# ── CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.main-header{background:linear-gradient(135deg,#1a1a2e,#0f3460);padding:20px 30px;border-radius:12px;margin-bottom:20px;color:white}
.source-badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:bold;margin-bottom:8px}
</style>""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
<h1>🛡️ FraudShield AI</h1>
<p style="opacity:.8;margin:0">Real-Time Fraud Detection & RAG-Powered Intelligence | Pathway + OpenAI</p>
</div>""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ System Status")
    df, from_pathway = get_df()

    if from_pathway:
        st.success("🟢 Pathway Pipeline: Active")
        st.caption("Reading from Pathway stream output")
    else:
        st.info("🔵 In-Memory Mode: Active")
        st.caption("Generating live transactions directly")

    try:
        r = requests.get(f"{RAG_SERVER_URL}/v1/statistics", timeout=2)
        st.success("🟢 RAG Server: Online")
    except:
        st.warning("🟡 RAG Server: Starting...")

    st.divider()
    auto_refresh = st.toggle("Auto-refresh (2s)", value=True)
    if st.button("🔄 Refresh Now"):
        st.rerun()
    st.divider()
    st.caption("**Active Fraud Rules:**")
    st.caption("• Amount > ₹5,000 → +40pts")
    st.caption("• Off-hours (00-06) → +30pts")
    st.caption("• Combo trigger → +20pts")
    st.caption("• High-risk merchant → +25pts")

# ── Tabs ─────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Live Dashboard","🚨 Fraud Alerts","🤖 AI Assistant"])

with tab1:
    if df.empty:
        st.info("⏳ Starting transaction stream...")
    else:
        total   = len(df)
        flagged = df[df["is_fraud_flag"]==True] if "is_fraud_flag" in df.columns else pd.DataFrame()
        critical= df[df["risk_level"]=="CRITICAL"] if "risk_level" in df.columns else pd.DataFrame()
        clean   = df[df["is_fraud_flag"]==False]  if "is_fraud_flag" in df.columns else df

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Transactions", total)
        c2.metric("🚨 Flagged", len(flagged), delta=f"{len(flagged)/max(total,1)*100:.1f}%", delta_color="inverse")
        c3.metric("🔴 Critical", len(critical), delta_color="inverse")
        c4.metric("✅ Clean", len(clean))

        if "risk_level" in df.columns:
            st.subheader("Risk Distribution")
            col_c, col_t = st.columns([1,2])
            with col_c:
                st.bar_chart(df["risk_level"].value_counts())
            with col_t:
                st.dataframe(
                    df[["transaction_id","amount","user_id","merchant","hour","risk_score","risk_level","fraud_reason"]]
                    .sort_values("risk_score", ascending=False).head(20),
                    use_container_width=True, hide_index=True
                )

with tab2:
    _, from_pathway = get_df()
    df2, _ = get_df()
    fraud = df2[df2["is_fraud_flag"]==True] if not df2.empty and "is_fraud_flag" in df2.columns else pd.DataFrame()

    if fraud.empty:
        st.info("✅ No fraud alerts yet — transactions are being processed.")
    else:
        st.subheader(f"🚨 {len(fraud)} Active Fraud Alerts")
        critical = fraud[fraud["risk_level"]=="CRITICAL"] if "risk_level" in fraud.columns else pd.DataFrame()
        if not critical.empty:
            st.error(f"🔴 {len(critical)} CRITICAL alerts require immediate action!")
            for _, row in critical.head(5).iterrows():
                with st.expander(f"🔴 {row.get('transaction_id','?')} | ₹{row.get('amount',0):,.0f} | {row.get('merchant','?')}"):
                    a,b = st.columns(2)
                    a.write(f"**User:** {row.get('user_id','?')}")
                    a.write(f"**Location:** {row.get('location','?')}")
                    b.write(f"**Risk Score:** {row.get('risk_score','?')}/100")
                    b.write(f"**Hour:** {row.get('hour','?')}:00")
                    st.warning(f"**Reason:** {row.get('fraud_reason','?')}")
        st.dataframe(
            fraud[["transaction_id","amount","user_id","merchant","hour","location","risk_score","risk_level","fraud_reason"]]
            .sort_values("risk_score", ascending=False),
            use_container_width=True, hide_index=True
        )

with tab3:
    st.subheader("🤖 FraudShield AI Assistant")
    st.caption("Ask anything about fraud policies or flagged transactions. Powered by Pathway RAG + GPT-4o mini.")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if not st.session_state.chat_history:
        st.write("**💡 Try asking:**")
        suggestions = [
            "Why are off-hours transactions flagged?",
            "What action for a CRITICAL risk transaction?",
            "Explain the combo fraud rule",
            "What are AML compliance requirements?",
        ]
        cols = st.columns(2)
        for i,s in enumerate(suggestions):
            if cols[i%2].button(s, key=f"s{i}"):
                st.session_state.chat_history.append({"role":"user","content":s})
                st.rerun()

    user_input = st.chat_input("Ask about fraud policies or transactions...")
    if user_input:
        st.session_state.chat_history.append({"role":"user","content":user_input})
        st.rerun()

    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                policy = query_rag(st.session_state.chat_history[-1]["content"])
                df3, _ = get_df()
                fraud3 = df3[df3["is_fraud_flag"]==True].head(10).to_string(index=False) if not df3.empty and "is_fraud_flag" in df3.columns else "No alerts yet."
                answer = ask_ai(st.session_state.chat_history[-1]["content"], fraud3, policy)
                st.write(answer)
                st.session_state.chat_history.append({"role":"assistant","content":answer})

if auto_refresh:
    time.sleep(2)
    st.rerun()