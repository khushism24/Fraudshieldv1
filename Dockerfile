FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create data directories
#RUN mkdir -p data/transactions data/output data/policies
CMD [*./start.sh*]

# Default command (overridden by docker-compose per service)
CMD ["python", "fraud_pipeline.py"]
