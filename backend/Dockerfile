FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY artifacts ./artifacts

RUN chmod +x scripts/docker_seed.sh \
    && mkdir -p artifacts data_store

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "-m", "scripts.generate_data"]
CMD ["python", "-m", "scripts.migrate", "up"]
CMD ["python", "-m", "scripts.build_agent_weekly"]
CMD ["python", "-m", "scripts.create_user"]
CMD ["python", "-m", "scripts.smoke_test"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
