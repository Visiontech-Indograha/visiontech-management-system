"""app/core/retention.py
Konstanta retensi data pribadi karyawan (UU PDP): berkas & data pribadi dihapus 30 hari setelah karyawan keluar
(`employee.separated_at`). Dipakai job terjadwal (`core/retention_job`) dan pemulihan karyawan (harus selaras)."""
from datetime import timedelta

PERSONAL_DATA_DAYS = 30
PERSONAL_DATA_WINDOW = timedelta(days=PERSONAL_DATA_DAYS)
