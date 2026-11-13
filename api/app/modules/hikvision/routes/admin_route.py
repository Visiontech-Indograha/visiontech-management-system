"""Admin perangkat Hikvision (login; izin manage:hikvision; HR dibatasi kantornya, OM/SA semua)."""
from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import require_permission
from app.core.errors import ValidationError
from app.core.list_params import ListParams, apply_list, check_date_range
from app.core.permissions import Permission
from app.core.security import CurrentUser
from app.core.time import jakarta_now
from app.modules.hikvision.dependencies import get_admin_service
from app.modules.hikvision.schemas import admin as s
from app.modules.hikvision.services.hikvision_admin_service import HikvisionAdminService

router = APIRouter(prefix="/hikvision", tags=["Hikvision admin"])
_IZIN = Depends(require_permission(Permission.MANAGE_HIKVISION))


def _base(request: Request) -> str:
    return str(request.base_url)


@router.get("/devices", response_model=list[s.PerangkatOut])
async def daftar_perangkat(
    response: Response, params: ListParams = Depends(), office_id: UUID | None = None,
    user: CurrentUser = _IZIN, svc: HikvisionAdminService = Depends(get_admin_service),
) -> list[s.PerangkatOut]:
    rows = await svc.daftar(user, office_id)
    def hay(r: s.PerangkatOut) -> tuple[object, ...]:
        return (r.name, r.serial_no, r.model, r.ip_address, r.office_name)

    return list(apply_list(rows, params, response, hay))


@router.post("/devices", response_model=s.PerangkatDibuat, status_code=201)
async def buat_perangkat(
    body: s.PerangkatBuat, request: Request, user: CurrentUser = _IZIN,
    svc: HikvisionAdminService = Depends(get_admin_service),
) -> s.PerangkatDibuat:
    """Buat perangkat. Token dan alamat penerima ditampilkan SEKALI di jawaban ini."""
    return await svc.buat(body, user, _base(request))


@router.get("/devices/{device_id}", response_model=s.PerangkatOut)
async def detail_perangkat(
    device_id: UUID, user: CurrentUser = _IZIN, svc: HikvisionAdminService = Depends(get_admin_service)
) -> s.PerangkatOut:
    return await svc.detail(device_id, user)


@router.patch("/devices/{device_id}", response_model=s.PerangkatOut)
async def ubah_perangkat(
    device_id: UUID, body: s.PerangkatUbah, user: CurrentUser = _IZIN,
    svc: HikvisionAdminService = Depends(get_admin_service),
) -> s.PerangkatOut:
    return await svc.ubah(device_id, body, user)


@router.delete("/devices/{device_id}", status_code=204)
async def hapus_perangkat(
    device_id: UUID, user: CurrentUser = _IZIN, svc: HikvisionAdminService = Depends(get_admin_service)
) -> Response:
    await svc.hapus(device_id, user)
    return Response(status_code=204)


@router.post("/devices/{device_id}/token", response_model=s.TokenBaru)
async def ganti_token(
    device_id: UUID, request: Request, user: CurrentUser = _IZIN,
    svc: HikvisionAdminService = Depends(get_admin_service),
) -> s.TokenBaru:
    """Ganti token penerima. Token lama langsung tidak berlaku; yang baru ditampilkan SEKALI."""
    return await svc.ganti_token(device_id, user, _base(request))


@router.get("/devices/{device_id}/status", response_model=s.StatusPerangkat)
async def status_perangkat(
    device_id: UUID, user: CurrentUser = _IZIN, svc: HikvisionAdminService = Depends(get_admin_service)
) -> s.StatusPerangkat:
    return await svc.status(device_id, user)


@router.get("/devices/{device_id}/mappings", response_model=list[s.PemetaanOut])
async def daftar_pemetaan(
    device_id: UUID, response: Response, params: ListParams = Depends(), user: CurrentUser = _IZIN,
    svc: HikvisionAdminService = Depends(get_admin_service),
) -> list[s.PemetaanOut]:
    rows = await svc.daftar_pemetaan(device_id, user)
    return list(apply_list(rows, params, response, lambda r: (r.employee_no_string, r.employee_no, r.full_name)))


@router.post("/devices/{device_id}/mappings", response_model=s.PemetaanOut, status_code=201)
async def buat_pemetaan(
    device_id: UUID, body: s.PemetaanBuat, user: CurrentUser = _IZIN,
    svc: HikvisionAdminService = Depends(get_admin_service),
) -> s.PemetaanOut:
    return await svc.buat_pemetaan(device_id, body, user)


@router.get("/devices/{device_id}/mappings/suggestions", response_model=s.UsulanPemetaan)
async def usulan_pemetaan(
    device_id: UUID, user: CurrentUser = _IZIN, svc: HikvisionAdminService = Depends(get_admin_service)
) -> s.UsulanPemetaan:
    """Usulan: nomor perangkat yang sama dengan nomor karyawan di kantor perangkat, dan yang tidak cocok."""
    return await svc.usulan(device_id, user)


@router.post("/devices/{device_id}/mappings/auto", response_model=s.PemetaanOtomatisOut)
async def pemetaan_otomatis(
    device_id: UUID, user: CurrentUser = _IZIN, svc: HikvisionAdminService = Depends(get_admin_service)
) -> s.PemetaanOtomatisOut:
    """Buat semua pemetaan yang cocok, lalu terapkan ke event lama yang belum terpetakan."""
    return await svc.otomatis(device_id, user)


@router.post("/devices/{device_id}/mappings/apply", response_model=s.PemetaanDiterapkan)
async def terapkan_pemetaan(
    device_id: UUID, user: CurrentUser = _IZIN, svc: HikvisionAdminService = Depends(get_admin_service)
) -> s.PemetaanDiterapkan:
    """Terapkan pemetaan ke event yang karyawannya masih kosong (per kelompok)."""
    return await svc.terapkan(device_id, user)


@router.patch("/devices/{device_id}/mappings/{map_id}", response_model=s.PemetaanOut)
async def ubah_pemetaan(
    device_id: UUID, map_id: UUID, body: s.PemetaanUbah, user: CurrentUser = _IZIN,
    svc: HikvisionAdminService = Depends(get_admin_service),
) -> s.PemetaanOut:
    return await svc.ubah_pemetaan(device_id, map_id, body, user)


@router.delete("/devices/{device_id}/mappings/{map_id}", status_code=204)
async def hapus_pemetaan(
    device_id: UUID, map_id: UUID, user: CurrentUser = _IZIN,
    svc: HikvisionAdminService = Depends(get_admin_service),
) -> Response:
    await svc.hapus_pemetaan(device_id, map_id, user)
    return Response(status_code=204)


@router.get("/devices/{device_id}/bayangan", response_model=s.BandingBayangan)
async def banding_bayangan(
    device_id: UUID, dari: date | None = None, sampai: date | None = None, user: CurrentUser = _IZIN,
    svc: HikvisionAdminService = Depends(get_admin_service),
) -> s.BandingBayangan:
    """Baca saja: tap mesin mode bayangan vs absen aplikasi per karyawan-hari. Bawaan 14 hari terakhir, maks 31 hari."""
    akhir = sampai or jakarta_now().date()
    mulai = dari or akhir - timedelta(days=14)
    check_date_range(mulai, akhir, start_name="dari", end_name="sampai")
    if (akhir - mulai).days > 30:
        raise ValidationError("Rentang paling lama 31 hari.")
    return await svc.banding_bayangan(device_id, mulai, akhir, user)
