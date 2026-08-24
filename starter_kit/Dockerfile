FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# pyqpanda 依赖 libcurl.so.4
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcurl4 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/submission
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Each vendor SDK has an isolated interpreter. SpinQit 0.2.4 requires ANTLR
# 4.9.x while the Braket stack requires ANTLR 4.13.x, so a single environment
# cannot represent the tested dependency graph.
COPY backend_requirements/ ./backend_requirements/
RUN python -m venv /opt/loomq-backends/spinq \
    && /opt/loomq-backends/spinq/bin/pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r backend_requirements/spinq.lock.txt \
    && python -m venv /opt/loomq-backends/originq \
    && /opt/loomq-backends/originq/bin/pip install --no-cache-dir -r backend_requirements/originq.lock.txt \
    && python -m venv /opt/loomq-backends/braket \
    && /opt/loomq-backends/braket/bin/pip install --no-cache-dir -r backend_requirements/braket.lock.txt
COPY . .

CMD ["python", "evaluator.py", "--level", "l1", "--target", "spinq,originq,braket", "--shots", "8192", "--json-out", "/tmp/loomq-public-report.json"]
