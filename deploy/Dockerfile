FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY compaq ./compaq
RUN pip install --no-cache-dir .

# 非 root 运行
RUN useradd -m compaq && mkdir -p /data && chown -R compaq /data /app
USER compaq
ENV COMPAQ_HOME=/data/compaq
VOLUME ["/data"]

EXPOSE 8642
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8642/healthz', timeout=2)"

# 首次启动自动建 demo 实例
CMD ["sh", "-c", "python -m compaq demo --frames 60 --no-color >/dev/null 2>&1; exec python -m compaq dashboard --host 0.0.0.0 --port 8642"]
