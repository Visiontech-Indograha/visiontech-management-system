"""
Kop, footer, dan sampul laporan survei memakai judul pekerjaan & klien nyata, bukan teks bawaan master
(dulu "PHR ZONA ROKAN" dan "INSTALATION" tercetak di setiap halaman).
"""
from __future__ import annotations

import io
import re
import zipfile
from decimal import Decimal

import pytest

from app.modules.exports.services.builders.survey_template import SurveyDoc, build_survey_docx

PROJECT = "Pemasangan CCTV Gedung Uji Timur"
CLIENT = "PT Contoh Klien Sejahtera"
LEFTOVERS = ("PHR ZONA ROKAN", "NEW CCTV INSTALATION", "NEW CCTV INSTALLATION AT PHR", "ZONA ROKAN",
             "SMO SOUTH AREA", "INSTALLASI BARU CCTV")


def _doc(fmt: str, project_title: str = PROJECT) -> SurveyDoc:
    return SurveyDoc(
        format=fmt, client=CLIENT, date_text="21 September 2026", activity_date_text="21 September 2026",
        location="Lokasi uji", purpose=project_title, activities=["Survey Lokasi"], narrative=["Uraian uji."],
        points=[], bom=[(  "Kabel", Decimal("10"), "m", "Umum")], team_name="Tim Uji", leader_name="Ketua Uji",
        member_names=["Anggota Uji"], project_title=project_title,
    )


def _parts_text(content: bytes) -> dict[str, str]:
    """Teks setiap bagian WordprocessingML (sampul, kop, footer) per berkas XML."""
    out = {}
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        for name in z.namelist():
            if re.match(r"word/(document|header\d*|footer\d*)\.xml$", name):
                out[name] = " ".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", z.read(name).decode("utf8")))
    return out


@pytest.mark.parametrize("fmt", ["ACS", "CCTV"])
def test_survey_header_footer_and_cover_show_project_not_master_text(fmt):
    text = _parts_text(build_survey_docx(_doc(fmt)))
    everything = " ".join(text.values())
    for leftover in LEFTOVERS:
        assert leftover not in everything, leftover
    headers = " ".join(v for k, v in text.items() if "header" in k)
    assert PROJECT in headers
    assert PROJECT in " ".join(v for k, v in text.items() if "footer" in k)
    assert PROJECT in text["word/document.xml"]


def test_missing_project_title_falls_back_to_client_name():
    text = _parts_text(build_survey_docx(_doc("CCTV", project_title="")))
    assert "PHR ZONA ROKAN" not in " ".join(text.values())
    assert CLIENT.upper() in " ".join(v for k, v in text.items() if "header" in k)
