"""Swedish Riksdagen SFS record parsing + citation helpers.

The Riksdagen open-data API returns JSON. A search (``dokumentlista``) wraps a list of
document stubs; a single act (``dokumentstatus``) wraps one richer ``dokument`` object. Both
carry the same key fields, so one parser handles either shape.

Citation contract (Art. 4 CONSTITUTION):
- ``eli_uri``: the official persistent document identifier
  ``https://data.riksdagen.se/dokument/<dok_id>``. Sweden does NOT publish native ELI (/eli/)
  URIs, so this field carries the equivalent stable identifier rather than a fabricated ELI.
- ``human_readable_citation``: the act title, which by Swedish convention embeds the SFS number
  (e.g. "Lag (2018:218) med kompletterande bestammelser till EU:s dataskyddsforordning").
- ``source_url``: the browsable data.riksdagen.se HTML page for the act.
"""

from __future__ import annotations

import json
import re
from typing import Any

DOC_BASE = "https://data.riksdagen.se/dokument"
_BET_RE = re.compile(r"^\s*(\d{4}):(\d+)\s*$")
_TOM_RE = re.compile(r"(?i)t\.o\.m\.?\s*(SFS\s*\d{4}:\d+)")


def dok_id_from_beteckning(beteckning: str) -> str | None:
    """Map an SFS number 'YYYY:N' to its Riksdagen dok_id 'sfs-YYYY-N'."""
    m = _BET_RE.match(beteckning)
    if not m:
        return None
    return f"sfs-{m.group(1)}-{m.group(2)}"


def _first(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return None


def _date_only(value: Any) -> str | None:
    if not value:
        return None
    return str(value).split(" ")[0].strip() or None


def parse_document(dok: dict[str, Any]) -> dict[str, Any]:
    """Build the citation contract from a Riksdagen document object (list stub or status)."""
    out: dict[str, Any] = {}

    dok_id = _first(dok, "dok_id", "id")
    sfs_number = _first(dok, "beteckning")
    title = _first(dok, "titel", "notisrubrik")
    year = _first(dok, "rm")
    authority = _first(dok, "organ")
    date_issued = _date_only(_first(dok, "datum"))
    subtitle = _first(dok, "undertitel", "subtitel")

    if dok_id:
        out["dok_id"] = dok_id
        out["eli_uri"] = f"{DOC_BASE}/{dok_id}"
        out["source_url"] = f"{DOC_BASE}/{dok_id}.html"
        out["text_url"] = f"{DOC_BASE}/{dok_id}.text"
    if sfs_number:
        out["sfs_number"] = sfs_number
    if title:
        out["title"] = title
        out["human_readable_citation"] = title
    if year:
        out["year"] = str(year)
    if authority:
        out["authority"] = authority
    if date_issued:
        out["date_issued"] = date_issued
    if subtitle:
        m = _TOM_RE.search(str(subtitle))
        if m:
            out["consolidated_through"] = m.group(1).replace("  ", " ")

    return out


def parse_search(json_text: str) -> tuple[int, list[dict[str, Any]]]:
    """Parse a ``dokumentlista`` response -> (total_hits, [contract dicts])."""
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return 0, []
    lista = data.get("dokumentlista") or {}
    total_raw = lista.get("@traffar") or "0"
    try:
        total = int(total_raw)
    except (ValueError, TypeError):
        total = 0
    docs = lista.get("dokument") or []
    if isinstance(docs, dict):  # single hit is returned as an object, not a list
        docs = [docs]
    return total, [parse_document(d) for d in docs if isinstance(d, dict)]


def _status_dokument(json_text: str) -> dict[str, Any] | None:
    try:
        data = json.loads(json_text)
    except (ValueError, TypeError):
        return None
    dok = (data.get("dokumentstatus") or {}).get("dokument")
    return dok if isinstance(dok, dict) else None


def parse_status(json_text: str) -> dict[str, Any] | None:
    """Parse a ``dokumentstatus`` response -> one contract dict (or None)."""
    dok = _status_dokument(json_text)
    return parse_document(dok) if dok is not None else None


def status_inline_text(json_text: str) -> str | None:
    """Extract the full consolidated text inlined in a ``dokumentstatus`` response.

    Riksdagen inlines the complete act text in ``dokumentstatus.dokument.text``; using it
    avoids a second request to the occasionally-flaky ``/dokument/<id>.text`` endpoint.
    """
    dok = _status_dokument(json_text)
    if dok is None:
        return None
    text = dok.get("text")
    if isinstance(text, str) and text.strip():
        return text
    return None
