import copy
import json
from pathlib import Path

import pytest

from ieee1547_check import check_settings, expected_defaults
from ieee1547_check.cli import main

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "site_settings_480v.json"


def good(category="III", profile="cat3"):
    trip = {k: {"pickup": v["pickup"], "time": v["time"]} for k, v in expected_defaults(profile).items()}
    return {"category": category, "profile": profile, "trip": trip}


def sev(findings, level):
    return [f for f in findings if f.severity == level]


@pytest.mark.parametrize("profile,cat", [("cat1", "I"), ("cat2", "II"), ("cat3", "III"), ("rule21", "III")])
def test_defaults_pass_clean(profile, cat):
    f = check_settings(good(cat, profile))
    assert not sev(f, "FAIL") and not sev(f, "WARN")


def test_category_specific_defaults():
    assert expected_defaults("cat2")["UV1"] == {"pickup": 0.70, "time": 10.0}
    assert expected_defaults("cat3")["UV1"] == {"pickup": 0.88, "time": 21.0}
    assert expected_defaults("cat1")["OF1"]["pickup"] == 61.2


def test_out_of_range_time_fails():
    s = good()
    s["trip"]["UV1"]["time"] = 60  # Cat III max 50 s
    msgs = [f.message for f in sev(check_settings(s), "FAIL")]
    assert any("clearing time 60" in m for m in msgs)


def test_cat2_rejects_cat3_ride_through_time():
    s = good("II", "cat2")
    s["trip"]["UV1"]["time"] = 30  # Cat II max 21 s
    assert sev(check_settings(s), "FAIL")


def test_ov2_is_fixed():
    s = good()
    s["trip"]["OV2"]["pickup"] = 1.25
    assert any(f.function == "OV2" for f in sev(check_settings(s), "FAIL"))


def test_stage_ordering():
    s = good()
    s["trip"]["UV2"]["time"] = 30  # slower than UV1 (21 s) and out of range
    fails = sev(check_settings(s), "FAIL")
    assert any(f.function == "UV2/UV1" for f in fails)


def test_continuous_band_warning():
    s = good()
    s["trip"]["OF1"]["pickup"] = 61.0  # allowed by range, inside continuous band
    warns = sev(check_settings(s), "WARN")
    assert any(f.function == "OF1" and "continuous" in f.message for f in warns)
    assert not sev(check_settings(s), "FAIL")


def test_missing_function():
    s = good()
    del s["trip"]["UF2"]
    assert any(f.function == "UF2" for f in sev(check_settings(s), "FAIL"))


def test_pickup_in_volts():
    s = good()
    s["nominal_voltage_v"] = 240
    s["trip"]["UV1"] = {"pickup_v": 211.2, "time": 21.0}
    assert not sev(check_settings(s), "FAIL")


def test_volt_var_shape():
    s = good(profile="rule21")
    s["volt_var"] = [[92, -30], [97, 0], [103, 0], [107, 30]]  # signs reversed
    assert any(f.function == "volt-var" for f in sev(check_settings(s), "FAIL"))


def test_example_flags_uv2_deviation():
    s = json.loads(EXAMPLE.read_text())
    f = check_settings(s)
    assert not sev(f, "FAIL")
    assert any(x.function == "UV2" for x in sev(f, "WARN"))


def test_cli_exit_codes(tmp_path, capsys):
    assert main([str(EXAMPLE)]) == 0
    bad = copy.deepcopy(good())
    bad["trip"]["OV1"]["pickup"] = 1.30
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad))
    assert main([str(p)]) == 1
