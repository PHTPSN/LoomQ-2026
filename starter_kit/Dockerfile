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

COPY backend_requirements/originq.lock.txt ./backend_requirements/originq.lock.txt
RUN python -m venv /opt/loomq-backends/originq \
    && /opt/loomq-backends/originq/bin/pip install --no-cache-dir \
        -r backend_requirements/originq.lock.txt
COPY . .

CMD ["python", "evaluator.py", "--level", "l1", "--target", "originq", "--shots", "8192", "--json-out", "/tmp/loomq-public-report.json"]
