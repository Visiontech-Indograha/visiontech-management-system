from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

API_ROOT = Path(__file__).resolve().parents[2]


def test_default_alembic_chain_targets_master_schema_v2() -> None:
    config = Config(str(API_ROOT / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)

    assert config.get_main_option("script_location").endswith("alembic_v2")
    assert scripts.get_heads() == ["v2_0007"]
    assert scripts.get_revision("v2_0001").down_revision is None
    assert scripts.get_revision("v2_0002").down_revision == "v2_0001"
    assert scripts.get_revision("v2_0003").down_revision == "v2_0002"
    assert scripts.get_revision("v2_0004").down_revision == "v2_0003"
    assert scripts.get_revision("v2_0005").down_revision == "v2_0004"
    assert scripts.get_revision("v2_0006").down_revision == "v2_0005"
    assert scripts.get_revision("v2_0007").down_revision == "v2_0006"


def test_legacy_v1_chain_remains_explicitly_available() -> None:
    config = Config(str(API_ROOT / "alembic-v1.ini"))
    scripts = ScriptDirectory.from_config(config)

    assert config.get_main_option("script_location").endswith("alembic")
    assert "0043_work_plan_flow_revamp" in {revision.revision for revision in scripts.walk_revisions()}
