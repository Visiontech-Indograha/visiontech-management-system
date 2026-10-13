"""
app/modules/work_types/repositories/work_type_repository.py

Repository akses data persistensi untuk entitas jenis pekerjaan (vms.work_type).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.4.
"""
from app.crud.crud_work_type import CRUDWorkType


class WorkTypeRepository(CRUDWorkType):
    """
    Repository akses data jenis pekerjaan dan template fotonya.
    """

