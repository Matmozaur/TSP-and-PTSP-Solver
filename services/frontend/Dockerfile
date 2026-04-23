FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install frontend dependencies only
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir \
    "streamlit>=1.28.0" \
    "plotly>=5.17.0" \
    "httpx>=0.25.0" \
    "pandas>=2.0.0" \
    "networkx>=3.0" \
    "numpy>=1.24.0"

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy frontend service code
COPY services/frontend/helpers/ ./helpers/
COPY services/frontend/streamlit_app.py ./streamlit_app.py
COPY services/frontend/.streamlit/ ./.streamlit/

RUN mkdir -p /app/media /app/results

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
