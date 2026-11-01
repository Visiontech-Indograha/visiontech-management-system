FROM python:3.15-slim

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

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Metadata citra (terbaca lewat `docker inspect` / deploy/status-layanan.sh). GIT_SHA & VMS_ENV diisi autodeploy.sh.
ARG GIT_SHA=tidak-diketahui
ARG VMS_ENV=tidak-diketahui
LABEL org.opencontainers.image.title="vms-api"       org.opencontainers.image.description="VMS API (FastAPI)"       org.opencontainers.image.revision="${GIT_SHA}"       org.opencontainers.image.source="https://github.com/Visiontech-Indograha/visiontech-management-system"       vms.layanan="api"       vms.lingkungan="${VMS_ENV}"       vms.port-dalam="8000"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
