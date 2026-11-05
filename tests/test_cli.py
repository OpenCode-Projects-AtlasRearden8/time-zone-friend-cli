import pytest

from tzfriend import cli


def run(tmp_path, *argv):
    store = str(tmp_path / "participants.json")
    extra = [] if "--file" in argv else ["--file", store]
    return cli.main(list(argv) + extra + ([] if extra else [])) if extra else cli.main(list(argv))


def test_full_flow_in_tmp_dir(tmp_path, capsys):
    assert cli.main(["add", "Alice", "new york", "--file", str(tmp_path / "p.json")]) == 0
    assert cli.main(["add", "Bob", "tokyo", "--file", str(tmp_path / "p.json")]) == 0
    assert cli.main(["list", "--file", str(tmp_path / "p.json")]) == 0
    out = capsys.readouterr().out
    assert "Alice" in out and "America/New_York" in out and "Asia/Tokyo" in out

    assert cli.main(["show", "--date", "2026-06-10", "--file", str(tmp_path / "p.json")]) == 0
    out = capsys.readouterr().out
    assert "Bob" in out and "UTC" in out

    assert cli.main(["overlap", "--date", "2026-06-10", "--file", str(tmp_path / "p.json")]) == 0
    out = capsys.readouterr().out
    assert "1." in out  # suggestions are numbered

    out_file = tmp_path / "call.ics"
    assert cli.main(["export", "--out", str(out_file), "--date", "2026-06-10", "--file", str(tmp_path / "p.json")]) == 0
    content = out_file.read_text(encoding="utf-8")
    assert "DTSTART:" in content and content.rstrip().endswith("END:VCALENDAR")


def test_export_slot_index_and_out_of_range(tmp_path, capsys):
    store = str(tmp_path / "p.json")
    cli.main(["add", "Solo", "berlin", "--file", store])
    out_file = tmp_path / "call.ics"
    assert cli.main(["export", "--out", str(out_file), "--file", store]) == 0
    assert out_file.exists()
    assert cli.main(["export", "9", "--out", str(out_file), "--file", store]) == 1
    out = capsys.readouterr().out
    assert "out of range" in out


def test_add_unknown_zone_lists_matches(tmp_path, capsys):
    code = cli.main(["add", "X", "atlantisa", "--file", str(tmp_path / "p.json")])
    assert code == 1
    out = capsys.readouterr().out
    assert "Could not resolve" in out


def test_zones_search_and_show(capsys):
    assert cli.main(["zones", "syd"]) == 0
    out = capsys.readouterr().out
    assert "Australia/Sydney" in out
    assert cli.main(["zones", "new york"]) == 0
    out = capsys.readouterr().out
    assert "America/New_York" in out


def test_remove_nonexistent_is_failure(tmp_path, capsys):
    code = cli.main(["remove", "Ghost", "--file", str(tmp_path / "p.json")])
    assert code == 1


def test_span_48_supported(tmp_path, capsys):
    store = str(tmp_path / "p.json")
    cli.main(["add", "A", "Pacific/Auckland", "--file", store])
    assert cli.main(["show", "--date", "2026-01-10", "--span", "48", "--file", store]) == 0
    assert cli.main(["overlap", "--date", "2026-01-10", "--span", "48", "--file", store]) == 0


def test_bad_hours_rejected(tmp_path):
    with pytest.raises(ValueError):
        cli.parse_hours("9-7")
    with pytest.raises(ValueError):
        cli.parse_hours("aa-bb")
    assert cli.parse_hours("7-23") == (7, 23)
