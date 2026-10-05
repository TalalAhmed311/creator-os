import copy
import json
from pathlib import Path

import jsonschema
import pytest

from pipeline.common import validate
from pipeline.validate import check_edl_semantics, validate_file

FIX = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("name,schema", [("plan.json", "plan"), ("edl.json", "edl"), ("carousel.json", "carousel")])
def test_samples_validate(name, schema):
    validate(json.loads((FIX / name).read_text()), schema)
    assert validate_file(FIX / name) == []


def test_plan_rejects_unknown_hook_type():
    plan = json.loads((FIX / "plan.json").read_text())
    plan["hooks"][0]["type"] = "clickbait"
    with pytest.raises(jsonschema.ValidationError):
        validate(plan, "plan")


def test_edl_semantics_catch_backwards_segment():
    edl = json.loads((FIX / "edl.json").read_text())
    bad = copy.deepcopy(edl)
    bad["segments"][0]["out"] = 10.0
    assert any("must be >" in e for e in check_edl_semantics(bad))
    assert check_edl_semantics(edl) == []
