# FraudShield AI — Fraud Detection Policies & Rules

## Rule 1: High-Value Transaction Alert
Any single transaction exceeding $5,000 is automatically flagged for review. 
Large transactions are common vectors for card fraud, account takeovers, and money laundering.
Action: Freeze transaction, notify user via SMS, escalate to Level-2 review team.

## Rule 2: Off-Hours Transaction Alert
Transactions occurring between midnight (00:00) and 06:00 local time are flagged.
Fraudsters often exploit overnight windows when cardholders are asleep and monitoring is reduced.
Action: Send push notification to cardholder, require 2FA to proceed.

## Rule 3: High-Value Off-Hours Combo (Critical)
Transactions above $1,000 AND occurring between 00:00–06:00 trigger a CRITICAL alert.
This combination is a strong indicator of account compromise.
Action: Immediately block card, initiate emergency review, contact customer within 1 hour.

## Rule 4: Rapid Successive Transactions
More than 3 transactions from the same user within 5 minutes is suspicious.
This pattern is typical of card-testing attacks where stolen cards are tested with small amounts.
Action: Temporary hold on account, require re-authentication.

## Rule 5: Geographic Anomaly
Transactions from locations inconsistent with the user's recent history are flagged.
A transaction in Mumbai followed by one in London within 2 hours is physically impossible.
Action: Flag for manual review, notify cardholder.

## Rule 6: Known High-Risk Merchants
Transactions at merchants in high-fraud categories (crypto exchanges, wire transfer services, 
gambling sites) are subject to enhanced monitoring regardless of amount.
Action: Require 2FA, log for compliance reporting.

## Compliance & Regulatory Notes
- All flagged transactions are logged for 7 years per RBI guidelines.
- AML (Anti-Money Laundering) rules require reporting transactions above ₹10 lakh.
- PCI-DSS compliance mandates real-time monitoring of all card transactions.
- GDPR/DPDP Act: All customer alerts must use consented communication channels.

## Escalation Matrix
- LOW risk: Log only
- MEDIUM risk (1 rule): Alert sent to cardholder
- HIGH risk (2 rules): Block transaction + cardholder alert
- CRITICAL risk (combo rule): Block card + emergency contact + manual review
