import json
import shutil

from grain_check import run_grain_check

from app.powerbi.mock import MockPowerBIClient


def test_grain_check_passes_on_stub(ctx, client):
    ok, msg = run_grain_check(ctx, client)
    assert ok
    assert "PASS" in msg


def test_grain_check_stops_when_item_rows_missing(ctx, settings, tmp_path):
    fixtures = tmp_path / "fixtures"
    shutil.copytree(settings.fixtures_dir, fixtures)
    item_file = fixtures / "drill_item_yoy.json"
    spec = json.loads(item_file.read_text())
    spec["result"]["tables"][0]["rows"] = []
    item_file.write_text(json.dumps(spec))

    ok, msg = run_grain_check(ctx, MockPowerBIClient(fixtures))
    assert not ok
    assert "STOP" in msg
    assert "item" in msg.lower()
