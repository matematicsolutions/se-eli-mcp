"""Offline parser tests against committed Riksdagen SFS fixtures."""

from __future__ import annotations

from pathlib import Path

from se_eli_mcp.citations import (
    dok_id_from_beteckning,
    parse_search,
    parse_status,
    status_inline_text,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_dok_id_from_beteckning():
    assert dok_id_from_beteckning("2018:218") == "sfs-2018-218"
    assert dok_id_from_beteckning("1949:105") == "sfs-1949-105"
    assert dok_id_from_beteckning("not-a-number") is None
    assert dok_id_from_beteckning("") is None


def test_parse_status_citation_contract():
    rec = parse_status(_load("get_act_2018_218.json"))
    assert rec is not None
    assert rec["dok_id"] == "sfs-2018-218"
    assert rec["sfs_number"] == "2018:218"
    assert "2018:218" in rec["title"]
    assert rec["human_readable_citation"] == rec["title"]
    # eli_uri = persistent document identifier (Sweden has no native /eli/).
    assert rec["eli_uri"] == "https://data.riksdagen.se/dokument/sfs-2018-218"
    assert "/eli/" not in rec["eli_uri"]
    assert rec["source_url"] == "https://data.riksdagen.se/dokument/sfs-2018-218.html"
    assert rec["text_url"] == "https://data.riksdagen.se/dokument/sfs-2018-218.text"
    assert rec["year"] == "2018"
    # consolidation marker parsed from the subtitle "t.o.m. SFS ...".
    assert rec["consolidated_through"].startswith("SFS 2025:")


def test_parse_search_returns_acts():
    total, records = parse_search(_load("search_dataskydd.json"))
    assert total >= 1
    assert records
    for rec in records:
        assert rec["dok_id"].startswith("sfs-")
        assert rec["human_readable_citation"]
        assert rec["eli_uri"].startswith("https://data.riksdagen.se/dokument/")
        assert rec["source_url"]


def test_status_inline_text():
    text = status_inline_text(_load("get_act_2018_218.json"))
    assert text and len(text) > 1000
    assert "§" in text  # Swedish statute paragraph marker
    assert status_inline_text("not json") is None
    assert status_inline_text('{"dokumentstatus": {}}') is None


def test_parse_garbage_is_empty():
    assert parse_search("not json") == (0, [])
    assert parse_status("not json") is None
    assert parse_status('{"unexpected": true}') is None
