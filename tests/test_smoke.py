"""Live smoke tests against the Riksdagen open-data API.

These hit the network (data.riksdagen.se). They are skipped automatically if the host is
unreachable. Run explicitly with:

    pytest tests/test_smoke.py
"""

from __future__ import annotations

import httpx
import pytest

from se_eli_mcp.server import se_get_act, se_get_text, se_search

GDPR_SFS = "2018:218"  # Lag med kompletterande bestammelser till EU:s dataskyddsforordning


def _live_or_skip() -> None:
    try:
        r = httpx.get(
            "https://data.riksdagen.se/dokumentlista/",
            params={"doktyp": "SFS", "utformat": "json", "sz": "1"},
            timeout=20.0,
        )
        r.raise_for_status()
    except Exception as exc:  # pragma: no cover - network gate
        pytest.skip(f"Riksdagen API not reachable: {exc}")


@pytest.mark.asyncio
async def test_smoke_search():
    _live_or_skip()
    result = await se_search("dataskydd")
    assert result.returned >= 1
    for act in result.items:
        assert act.eli_uri and act.human_readable_citation and act.source_url
        assert act.sfs_number


@pytest.mark.asyncio
async def test_smoke_get_act():
    _live_or_skip()
    act = await se_get_act(GDPR_SFS)
    assert act.dok_id == "sfs-2018-218"
    assert act.sfs_number == GDPR_SFS
    assert "2018:218" in act.title
    assert act.eli_uri == "https://data.riksdagen.se/dokument/sfs-2018-218"
    assert "/eli/" not in act.eli_uri


@pytest.mark.asyncio
async def test_smoke_get_text():
    _live_or_skip()
    text = await se_get_text(GDPR_SFS)
    assert text.dok_id == "sfs-2018-218"
    assert text.sfs_number == GDPR_SFS
    assert text.content and text.byte_size and text.byte_size > 5_000
    assert "§" in text.content  # Swedish statute paragraph marker
    assert text.eli_uri and text.human_readable_citation and text.source_url
