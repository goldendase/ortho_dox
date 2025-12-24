FROM python:3.12-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (build context is api/ directory)
COPY . ./api/

# Create log directory
RUN mkdir -p /app/log

# Expose port (Railway will set PORT env var)
EXPOSE 8080

# Run with uvicorn - Railway sets PORT, we default to 8080
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
