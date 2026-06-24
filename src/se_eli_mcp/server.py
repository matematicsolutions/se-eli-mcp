"""FastMCP entry point - Swedish statutes (SFS) via the Riksdagen open-data API.

Run:

    python -m se_eli_mcp.server

Configuration via env:

- ``SE_ELI_CACHE_DIR`` (default ``~/.matematic/cache/se-eli``)
- ``SE_ELI_AUDIT_DIR`` (default ``~/.matematic/audit``)
- ``SE_ELI_BASE_URL`` (default ``https://data.riksdagen.se``)
"""

from __future__ import annotations

import os
import re

import httpx
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .audit import AuditLogger, hash_input, timer
from .citations import (
    dok_id_from_beteckning,
    parse_search,
    parse_status,
    status_inline_text,
)
from .client import DEFAULT_BASE_URL, RiksdagenClient, SeError
from .models import LawText, SearchResult, SfsAct

INSTRUCTIONS = """\
This MCP server exposes Swedish statutes (SFS, Svensk forfattningssamling) through the Riksdagen (parliament) open-data API (data.riksdagen.se, keyless). Riksdagen serves the consolidated text of each act. Every response carries a stable `eli_uri`, a `human_readable_citation` and a `source_url` (the citation contract).

## Call order

1. `se_search` - free-text search over SFS statutes (title and full text). Returns acts, each with `sfs_number` (e.g. `2018:218`), `eli_uri`, `human_readable_citation`, `source_url`.
2. `se_get_act` - metadata for one act by its SFS number (`sfs_number`, e.g. `2018:218`): title, authority, date, `consolidated_through`.
3. `se_get_text` - the full consolidated plain text of one act by its SFS number.

## Hard constraints

- **eli_uri is the citability key, but Sweden does NOT publish native ELI (/eli/) URIs.** `eli_uri` therefore carries the official persistent document identifier (`https://data.riksdagen.se/dokument/<dok_id>`), and the SFS number is the canonical citation. Never fabricate a `/eli/` URI.
- **Cite the SFS number** - Swedish law is cited as "SFS 2018:218"; the act title already embeds it.
- **Every response has `human_readable_citation` + `source_url`** - cite both to the user.
- **Consolidated text** - `consolidated_through` reports the last amendment folded in (the "andrad t.o.m." marker). Relay it so the user knows the version.
- **No modification of official text** - returned verbatim from Riksdagen.
- **Audit log JSONL** - every tool call appends to `~/.matematic/audit/se-eli-mcp.jsonl`.

## Error iteration

Tools return a structured error with a `[code]` prefix:
- `invalid_arg` - a parameter is missing or malformed (e.g. an SFS number not shaped like `2018:218`).
- `not_found` - no act exists for that SFS number / no hits for the query.
- `upstream_error` - a Riksdagen API error (HTTP, timeout, malformed JSON). Retry once before surfacing.

## Response style

- Cite acts as `human_readable_citation` with the identifier: "Lag (2018:218) ..., https://data.riksdagen.se/dokument/sfs-2018-218".
- NEVER invent an SFS number, a title or an identifier - take each from the tool output.
"""

_BET_RE = re.compile(r"^\d{4}:\d+$")
_MAX_SEARCH_RECORDS = 20


class ToolError(Exception):
    """Structured error for se-eli MCP tools - visible to the LLM with a [code] prefix."""

    VALID_CODES = frozenset({"invalid_arg", "not_found", "upstream_error"})

    def __init__(self, code: str, message: str):
        if code not in self.VALID_CODES:
            raise ValueError(f"Unknown ToolError code: {code}. Valid: {sorted(self.VALID_CODES)}")
        self.code = code
        super().__init__(f"[{code}] {message}")


READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    destructiveHint=False,
    openWorldHint=True,
)

mcp: FastMCP = FastMCP(name="se-eli-mcp", instructions=INSTRUCTIONS)


def _base_url() -> str:
    return os.environ.get("SE_ELI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _audit() -> AuditLogger:
    return AuditLogger()


def _map_upstream(exc: Exception) -> Exception:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404:
        return ToolError("not_found", "No document found in the Riksdagen repository.")
    if isinstance(exc, (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException)):
        return ToolError("upstream_error", f"Riksdagen API error: {type(exc).__name__}: {exc}")
    if isinstance(exc, SeError):
        return ToolError("upstream_error", str(exc))
    return exc


def _resolve_dok_id(sfs_number: str) -> tuple[str, str]:
    cleaned = sfs_number.strip()
    if not _BET_RE.match(cleaned):
        raise ToolError("invalid_arg", f"sfs_number={sfs_number!r} must look like '2018:218'.")
    dok_id = dok_id_from_beteckning(cleaned)
    if not dok_id:
        raise ToolError("invalid_arg", f"cannot derive dok_id from {sfs_number!r}.")
    return cleaned, dok_id


# ---------------------------------------------------------------------------
# se_search
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def se_search(query: str) -> SearchResult:
    """Search Swedish statutes (SFS) by free text (title and full text).

    Args:
        query: e.g. ``"dataskydd"``.

    Returns:
        ``SearchResult`` with ``items: list[SfsAct]``, each carrying the citation contract.
    """
    audit = _audit()
    if not query or not query.strip():
        raise ToolError("invalid_arg", "query must be a non-empty string.")
    input_hash = hash_input({"query": query})

    with timer() as t:
        try:
            async with RiksdagenClient(base_url=_base_url()) as client:
                raw = await client.search(query, maximum_records=_MAX_SEARCH_RECORDS)
        except Exception as exc:
            audit.log(tool="se_search", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    total, records = parse_search(raw)
    items = [SfsAct.model_validate(r) for r in records]
    result = SearchResult(query=query, total_matched=total, returned=len(items), items=items)
    audit.log(tool="se_search", input_hash=input_hash, output_count_or_size=len(items),
              duration_ms=t.duration_ms, status="ok")
    return result


# ---------------------------------------------------------------------------
# se_get_act
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def se_get_act(sfs_number: str) -> SfsAct:
    """Fetch metadata for a Swedish statute by its SFS number.

    Args:
        sfs_number: e.g. ``"2018:218"``.

    Returns:
        ``SfsAct`` with ``eli_uri``, ``human_readable_citation``, ``source_url``.
    """
    audit = _audit()
    cleaned, dok_id = _resolve_dok_id(sfs_number)
    input_hash = hash_input({"sfs_number": cleaned})

    with timer() as t:
        try:
            async with RiksdagenClient(base_url=_base_url()) as client:
                raw = await client.get_status(dok_id)
        except Exception as exc:
            audit.log(tool="se_get_act", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    record = parse_status(raw)
    if not record or not record.get("dok_id"):
        raise ToolError("not_found", f"No SFS act {cleaned}.")
    act = SfsAct.model_validate(record)
    audit.log(tool="se_get_act", input_hash=input_hash, output_count_or_size=1,
              duration_ms=t.duration_ms, status="ok")
    return act


# ---------------------------------------------------------------------------
# se_get_text
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def se_get_text(sfs_number: str) -> LawText:
    """Fetch the full consolidated plain text of a Swedish statute by its SFS number.

    Args:
        sfs_number: e.g. ``"2018:218"``.

    Returns:
        ``LawText`` with the citation contract and ``content`` (consolidated plain text).
    """
    audit = _audit()
    cleaned, dok_id = _resolve_dok_id(sfs_number)
    input_hash = hash_input({"sfs_number": cleaned})

    with timer() as t:
        try:
            async with RiksdagenClient(base_url=_base_url()) as client:
                meta_raw = await client.get_status(dok_id)
                record = parse_status(meta_raw)
                if not record or not record.get("dok_id"):
                    raise ToolError("not_found", f"No SFS act {cleaned}.")
                # Prefer the full text inlined in dokumentstatus (one call, robust);
                # fall back to the standalone .text endpoint only if it is absent.
                content = status_inline_text(meta_raw)
                if not content:
                    content = await client.get_text(dok_id)
        except ToolError:
            audit.log(tool="se_get_text", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error="not_found")
            raise
        except Exception as exc:
            audit.log(tool="se_get_text", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    if not content.strip():
        raise ToolError("not_found", f"No text available for SFS {cleaned}.")
    result = LawText(
        dok_id=dok_id,
        sfs_number=record.get("sfs_number") or cleaned,
        eli_uri=record.get("eli_uri"),
        human_readable_citation=record.get("human_readable_citation"),
        source_url=record.get("source_url"),
        text_url=record.get("text_url"),
        consolidated_through=record.get("consolidated_through"),
        content=content,
        byte_size=len(content.encode("utf-8")),
    )
    audit.log(tool="se_get_text", input_hash=input_hash, output_count_or_size=result.byte_size or 0,
              duration_ms=t.duration_ms, status="ok")
    return result


def main() -> None:
    """Run the MCP server over stdio (default for Claude Code)."""
    mcp.run()


if __name__ == "__main__":
    main()
