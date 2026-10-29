# Build from the repo root: docker compose -f buyer_finder/web/docker-compose.yml up -d --build
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BUYER_FINDER_DATA=/data
WORKDIR /app
COPY buyer_finder/web/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && useradd -u 1000 -m bf && mkdir -p /data && chown bf /data
COPY buyer_finder /app/buyer_finder
USER bf
EXPOSE 8000
# One worker keeps background-enrichment progress in memory; threads handle concurrent requests
CMD ["gunicorn", "-w", "1", "--threads", "4", "--timeout", "120", "-b", "0.0.0.0:8000", "buyer_finder.web.app:app"]
