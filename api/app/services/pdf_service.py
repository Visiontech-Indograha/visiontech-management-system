"""
app/services/pdf_service.py
Render PDF menggunakan WeasyPrint + Jinja2.
Semua dokumen (SK, adendum, BAST, laporan akhir) dirender di sini.
"""
from __future__ import annotations

import base64
import io
import qrcode
from pathlib import Path
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.plan_repo import PlanRepo
from app.core.errors import NotFoundError

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )


def _qr_to_base64(data: str, size: int = 10, border: int = 2) -> str:
    """Generate QR code dan kembalikan sebagai string base64 PNG."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class PdfService:
    def __init__(self, db: AsyncSession, base_url: str = "http://localhost") -> None:
        self.db = db
        self.plan_repo = PlanRepo(db)
        self.base_url = base_url
        self.jinja = _get_jinja_env()

    async def render_sk_pdf(self, plan_id: UUID, org_id: UUID) -> bytes:
        """Render PDF Surat Keputusan + QR code verifikasi."""
        plan = await self.plan_repo.get_by_id(plan_id, org_id)
        if not plan:
            raise NotFoundError("SK")
        days = await self.plan_repo.list_days(plan_id)

        # Ambil dokumen terbit terakhir
        doc = await self.plan_repo.fetchone(
            """
            SELECT * FROM vms.plan_document
            WHERE work_plan_id = :plan ORDER BY version DESC LIMIT 1
            """,
            {"plan": plan_id},
        )

        qr_data = f"{self.base_url}/verify/{doc.id}" if doc else ""
        qr_b64 = _qr_to_base64(qr_data) if qr_data else ""

        template = self.jinja.get_template("sk.html.j2")
        html = template.render(
            plan=dict(plan._mapping),
            days=[dict(d._mapping) for d in days],
            document=dict(doc._mapping) if doc else {},
            qr_base64=qr_b64,
            verify_url=qr_data,
        )
        return self._html_to_pdf(html)

    async def render_bast_pdf(self, return_id: UUID, org_id: UUID) -> bytes:
        """Render PDF Berita Acara Serah Terima Aset."""
        row = await self.plan_repo.fetchone(
            """
            SELECT ar.*, a.name AS asset_name, a.asset_code,
                   e.full_name AS returner_name, wp.title AS plan_title
            FROM vms.asset_return ar
            JOIN vms.asset_allocation al ON ar.allocation_id = al.id
            JOIN vms.asset a ON al.asset_id = a.id
            JOIN vms.work_plan wp ON al.work_plan_id = wp.id
            LEFT JOIN vms.employee e ON ar.returned_by = e.id
            WHERE ar.id = :id AND a.organization_id = :org
            """,
            {"id": return_id, "org": org_id},
        )
        if not row:
            raise NotFoundError("BAST")

        template = self.jinja.get_template("bast.html.j2")
        html = template.render(bast=dict(row._mapping))
        return self._html_to_pdf(html)

    @staticmethod
    def _html_to_pdf(html: str) -> bytes:
        """Render HTML ke PDF bytes via WeasyPrint."""
        try:
            from weasyprint import HTML, CSS
            buf = io.BytesIO()
            HTML(string=html).write_pdf(buf)
            return buf.getvalue()
        except ImportError:
            raise RuntimeError(
                "WeasyPrint tidak terpasang. Jalankan: pip install weasyprint"
            )
