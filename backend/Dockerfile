FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install uv & project dependencies
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
RUN uv pip install . --system

# Copy app code
COPY . .

# Expose backend port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "asyncio"]
