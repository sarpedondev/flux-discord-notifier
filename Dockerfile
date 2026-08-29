FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN python -m pip wheel --wheel-dir /wheels .

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/notifier/.local/bin:$PATH

RUN groupadd --gid 10001 notifier \
    && useradd --uid 10001 --gid notifier --create-home --shell /usr/sbin/nologin notifier

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/* && rm -rf /wheels

USER 10001:10001
WORKDIR /app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]

CMD ["uvicorn", "flux_discord_notifier.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
