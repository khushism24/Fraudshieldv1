"""
fraud_pipeline.py
Pathway real-time streaming pipeline for fraud detection.
Ingests transaction CSV streams, applies detection rules,
and writes flagged alerts to output.
"""
import os
import pathway as pw

# ── Schema ──────────────────────────────────────────────────────────────
class TransactionSchema(pw.Schema):
    transaction_id: str
    amount: float
    user_id: str
    hour: int
    merchant: str
    location: str
    card_type: str
    is_high_risk_merchant: str


# ── Helper functions ─────────────────────────────────────────────────────
def compute_risk_score(amount: float, hour: int, is_high_risk: str) -> int:
    score = 0
    if amount > 5000:
        score += 40
    if hour < 6:
        score += 30
    if amount > 1000 and hour < 6:
        score += 20  # Combo bonus
    if is_high_risk == "True":
        score += 25
    return min(score, 100)


def compute_fraud_reason(amount: float, hour: int, is_high_risk: str) -> str:
    reasons = []
    if amount > 5000:
        reasons.append(f"HIGH AMOUNT (${amount:,.2f} > $5000)")
    if hour < 6:
        reasons.append(f"OFF-HOURS (hour={hour}:00, between 00:00-06:00)")
    if amount > 1000 and hour < 6:
        reasons.append("CRITICAL COMBO (high-value + off-hours)")
    if is_high_risk == "True":
        reasons.append("HIGH-RISK MERCHANT CATEGORY")
    return " | ".join(reasons) if reasons else "CLEAN"


def compute_risk_level(score: int) -> str:
    if score >= 70:
        return "CRITICAL"
    elif score >= 50:
        return "HIGH"
    elif score >= 30:
        return "MEDIUM"
    elif score > 0:
        return "LOW"
    return "CLEAN"


def is_flagged(score: int) -> bool:
    return score >= 30


# ── Pipeline ─────────────────────────────────────────────────────────────
print("[Pipeline] Starting Pathway fraud detection pipeline...")
print("[Pipeline] Watching ./data/transactions/ for new transaction files...")

# 1. Ingest streaming CSV files from watched directory
transactions = pw.io.csv.read(
    path="./data/transactions/",
    schema=TransactionSchema,
    mode="streaming",
    autocommit_duration_ms=1000,
)

# 2. Apply fraud detection rules and compute risk
enriched = transactions.select(
    transaction_id=pw.this.transaction_id,
    amount=pw.this.amount,
    user_id=pw.this.user_id,
    hour=pw.this.hour,
    merchant=pw.this.merchant,
    location=pw.this.location,
    card_type=pw.this.card_type,
    risk_score=pw.apply(
        compute_risk_score,
        pw.this.amount,
        pw.this.hour,
        pw.this.is_high_risk_merchant,
    ),
    fraud_reason=pw.apply(
        compute_fraud_reason,
        pw.this.amount,
        pw.this.hour,
        pw.this.is_high_risk_merchant,
    ),
)

# 3. Add risk level column
enriched = enriched.select(
    *pw.this,
    risk_level=pw.apply(compute_risk_level, pw.this.risk_score),
    is_fraud_flag=pw.apply(is_flagged, pw.this.risk_score),
)

# 4. Write ALL transactions (for dashboard view)
os.makedirs("./data/output", exist_ok=True)
pw.io.csv.write(enriched, "./data/output/all_transactions.csv")

# 5. Write only flagged fraud alerts
fraud_alerts = enriched.filter(pw.this.is_fraud_flag == True)
pw.io.csv.write(fraud_alerts, "./data/output/fraud_alerts.csv")

print("[Pipeline] Pipeline configured. Running...")
pw.run()
