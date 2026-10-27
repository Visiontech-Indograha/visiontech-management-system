from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.work_plans.schemas.daily_plan_schema import DailyPlanCreate


def test_daily_plan_can_be_created_before_site_location_is_known():
    plan = DailyPlanCreate(
        division_id=uuid4(),
        team_id=uuid4(),
        work_date=datetime.now(UTC).date(),
    )

    assert plan.site_name is None
    assert plan.site_lat is None
    assert plan.site_lng is None


@pytest.mark.parametrize(
    ("site_lat", "site_lng"),
    [("1.2", None), (None, "101.4")],
)
def test_daily_plan_rejects_partial_site_coordinates(site_lat, site_lng):
    with pytest.raises(ValidationError, match="Latitude dan longitude"):
        DailyPlanCreate(
            division_id=uuid4(),
            team_id=uuid4(),
            work_date=datetime.now(UTC).date(),
            site_lat=site_lat,
            site_lng=site_lng,
        )
