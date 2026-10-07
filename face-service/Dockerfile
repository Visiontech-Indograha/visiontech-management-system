# Layanan inferensi wajah VMS. Model dibakukan ke citra supaya kontainer tidak mengunduh saat mulai.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ORT_DISABLE_TELEMETRY=1 \
    INSIGHTFACE_ROOT=/models \
    FACE_MODEL_PACK=buffalo_s

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 libxcb1 libx11-6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Unduh paket model (lisensi riset non-komersial InsightFace; lihat README) saat build, bukan saat jalan.
RUN python -c "from insightface.app import FaceAnalysis; FaceAnalysis(name='buffalo_s', root='/models', allowed_modules=['detection','recognition'], providers=['CPUExecutionProvider'])"

COPY main.py rules.py .

RUN useradd --system --no-create-home face && chown -R face /models
USER face

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if b'\"ok\"' in urllib.request.urlopen('http://127.0.0.1:8001/health').read() else 1)"

# Satu proses: model dimuat sekali; konkurensi dibatasi FACE_MAX_CONCURRENCY.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
