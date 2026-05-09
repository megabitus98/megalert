FROM python:3.12-slim

WORKDIR /megalert

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system megalert && adduser --system --ingroup megalert megalert
ENV HOME=/tmp
USER megalert

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "--worker-tmp-dir", "/tmp", "server:flask"]
