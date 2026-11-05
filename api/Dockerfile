FROM python:3.12-slim

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Pratinjau laporan survei (docs/37): .docx -> PDF dengan LibreOffice headless; Carlito/Caladea = metrik
# Calibri/Cambria sehingga tata letak sama dengan dokumen Word aslinya.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer-nogui \
    fonts-crosextra-carlito \
    fonts-crosextra-caladea \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Proses API berjalan sebagai pengguna non-root (F-01). HOME dipakai LibreOffice (profil konversi .docx -> PDF).
RUN useradd --system --uid 10001 --user-group --create-home --home-dir /home/vms --shell /usr/sbin/nologin vms
ENV HOME=/home/vms

# Dependensi dulu (cache lapisan efektif selama requirements.txt tidak berubah), kode aplikasi belakangan.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Folder tulis untuk runtime. uploads/ dikosongkan (foto/dokumen tidak masuk image; lihat .dockerignore).
RUN mkdir -p /app/uploads /app/backups && chown vms:vms /app/uploads /app/backups

# Proses berjalan sebagai uid 10001 (vms). Di server, folder rilis APK (deploy/pasang-rilis-apk.sh) di-mount
# read-only ke /srv/rilis: folder host itu harus bisa dibaca uid 10001. Rute /uploads (app/main.py) ditangani PR lain.
USER vms

# Metadata citra (terbaca lewat `docker inspect` / deploy/status-layanan.sh). GIT_SHA & VMS_ENV diisi autodeploy.sh.
ARG GIT_SHA=tidak-diketahui
ARG VMS_ENV=tidak-diketahui
LABEL org.opencontainers.image.title="vms-api"       org.opencontainers.image.description="VMS API (FastAPI)"       org.opencontainers.image.revision="${GIT_SHA}"       org.opencontainers.image.source="https://github.com/Visiontech-Indograha/visiontech-management-system"       vms.layanan="api"       vms.lingkungan="${VMS_ENV}"       vms.port-dalam="8000"

# Liveness tanpa DB (/health). Python ada di citra; curl tidak dipasang.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
