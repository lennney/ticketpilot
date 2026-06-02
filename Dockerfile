# TicketPilot Docker 部署配置

# Backend
FROM python:3.11-slim as backend

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend code
COPY src/ src/
COPY pyproject.toml .
COPY uv.lock .

# Install Python dependencies
RUN pip install uv && uv sync --no-dev

# Copy frontend
COPY frontend/ frontend/

# Build frontend
RUN apt-get update && apt-get install -y nodejs npm && \
    cd frontend && npm install && npm run build && \
    apt-get remove -y nodejs npm && apt-get autoremove -y

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run backend
CMD ["uv", "run", "uvicorn", "ticketpilot.api:app", "--host", "0.0.0.0", "--port", "8000"]
