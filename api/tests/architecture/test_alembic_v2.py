from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

API_ROOT = Path(__file__).resolve().parents[2]


def test_default_alembic_chain_targets_master_schema_v2() -> None:
    config = Config(str(API_ROOT / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)

    assert config.get_main_option("script_location").endswith("alembic_v2")
    assert scripts.get_heads() == ["v2_0041"]
    assert scripts.get_revision("v2_0041").down_revision == "v2_0040"
    assert scripts.get_revision("v2_0040").down_revision == "v2_0039"
    assert scripts.get_revision("v2_0039").down_revision == "v2_0038"
    assert scripts.get_revision("v2_0038").down_revision == "v2_0037"
    assert scripts.get_revision("v2_0037").down_revision == "v2_0036"
    assert scripts.get_revision("v2_0036").down_revision == "v2_0035"
    assert scripts.get_revision("v2_0035").down_revision == "v2_0034"
    assert scripts.get_revision("v2_0001").down_revision is None
    assert scripts.get_revision("v2_0002").down_revision == "v2_0001"
    assert scripts.get_revision("v2_0003").down_revision == "v2_0002"
    assert scripts.get_revision("v2_0004").down_revision == "v2_0003"
    assert scripts.get_revision("v2_0005").down_revision == "v2_0004"
    assert scripts.get_revision("v2_0006").down_revision == "v2_0005"
    assert scripts.get_revision("v2_0007").down_revision == "v2_0006"
    assert scripts.get_revision("v2_0008").down_revision == "v2_0007"
    assert scripts.get_revision("v2_0009").down_revision == "v2_0008"
    assert scripts.get_revision("v2_0010").down_revision == "v2_0009"
    assert scripts.get_revision("v2_0011").down_revision == "v2_0010"
    assert scripts.get_revision("v2_0013").down_revision == "v2_0012"
    assert scripts.get_revision("v2_0014").down_revision == "v2_0013"
    assert scripts.get_revision("v2_0015").down_revision == "v2_0014"
    assert scripts.get_revision("v2_0016").down_revision == "v2_0015"
    assert scripts.get_revision("v2_0017").down_revision == "v2_0016"
    assert scripts.get_revision("v2_0018").down_revision == "v2_0017"
    assert scripts.get_revision("v2_0019").down_revision == "v2_0018"
    assert scripts.get_revision("v2_0020").down_revision == "v2_0019"
    assert scripts.get_revision("v2_0024").down_revision == "v2_0023"
    assert scripts.get_revision("v2_0025").down_revision == "v2_0024"
    assert scripts.get_revision("v2_0026").down_revision == "v2_0025"
    assert scripts.get_revision("v2_0027").down_revision == "v2_0026"
    assert scripts.get_revision("v2_0028").down_revision == "v2_0027"
    assert scripts.get_revision("v2_0029").down_revision == "v2_0028"
    assert scripts.get_revision("v2_0030").down_revision == "v2_0029"
    assert scripts.get_revision("v2_0031").down_revision == "v2_0030"
    assert scripts.get_revision("v2_0032").down_revision == "v2_0031"


def test_legacy_v1_chain_remains_explicitly_available() -> None:
    # Rantai legacy v1 sudah resmi dipensiunkan & dibersihkan pada Work Order Revamp (Fase 1)
    assert not (API_ROOT / "alembic-v1.ini").exists()
    assert not (API_ROOT / "alembic").exists()
