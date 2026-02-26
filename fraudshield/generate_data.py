"""
generate_data.py
Simulates a real-time bank transaction stream by writing CSV files
into the watched directory every few seconds.
"""
import csv
import os
import random
import time
import uuid
from datetime import datetime

OUTPUT_DIR = "./data/transactions"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MERCHANTS = [
    "Amazon", "Flipkart", "Swiggy", "Zomato", "BookMyShow",
    "BigBasket", "Myntra", "Uber", "Ola", "Netflix",
    "CryptoExchange_BuyBit", "WireTransfer_Global", "CasinoRoyal",
    "MedPlus Pharmacy", "IRCTC", "Reliance Mart", "D-Mart",
]

HIGH_RISK_MERCHANTS = {"CryptoExchange_BuyBit", "WireTransfer_Global", "CasinoRoyal"}

USERS = [f"USER_{i:04d}" for i in range(1, 51)]

LOCATIONS = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Surat"
]

CARD_TYPES = ["Visa", "Mastercard", "RuPay", "Amex"]

file_counter = 0


def generate_transaction():
    """Generate one synthetic transaction, occasionally injecting fraud patterns."""
    rand = random.random()
    hour = datetime.now().hour

    if rand < 0.15:
        # Fraud pattern: high amount
        amount = round(random.uniform(5001, 25000), 2)
        hour = random.randint(0, 5)  # off hours too
    elif rand < 0.25:
        # Fraud pattern: off hours only
        amount = round(random.uniform(500, 4999), 2)
        hour = random.randint(0, 5)
    else:
        # Normal transaction
        amount = round(random.uniform(50, 4500), 2)
        hour = random.randint(6, 23)

    merchant = random.choice(MERCHANTS)

    return {
        "transaction_id": str(uuid.uuid4())[:8].upper(),
        "amount": amount,
        "user_id": random.choice(USERS),
        "hour": hour,
        "merchant": merchant,
        "location": random.choice(LOCATIONS),
        "card_type": random.choice(CARD_TYPES),
        "is_high_risk_merchant": str(merchant in HIGH_RISK_MERCHANTS),
    }


def write_batch(transactions):
    global file_counter
    file_counter += 1
    filename = os.path.join(OUTPUT_DIR, f"txn_batch_{file_counter:06d}.csv")
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=transactions[0].keys())
        writer.writeheader()
        writer.writerows(transactions)
    print(f"[Generator] Wrote {len(transactions)} transactions → {filename}")


if __name__ == "__main__":
    print("[Generator] Starting transaction stream... Press Ctrl+C to stop.")
    while True:
        batch_size = random.randint(3, 8)
        batch = [generate_transaction() for _ in range(batch_size)]
        write_batch(batch)
        time.sleep(2)  # New batch every 2 seconds
