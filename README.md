# se-eli-mcp

<!-- mcp-name: io.github.matematicsolutions/se-eli-mcp -->


## Install (one command)

Published on PyPI + MCP Registry (`io.github.matematicsolutions/se-eli-mcp`). Run without cloning:

```bash
uvx se-eli-mcp
```

Configure your MCP client (stdio):

```json
{ "mcpServers": { "se-eli-mcp": { "command": "uvx", "args": ["se-eli-mcp"] } } }
```

### Windows 11 with Smart App Control

Smart App Control blocks unsigned executables, which covers `uvx.exe`, `pip.exe`
and the `se-eli-mcp.exe` launcher that pip writes at install time. The `python.exe` and
`py.exe` from the python.org installer are signed by the Python Software
Foundation, so running the module through the interpreter works:

```bash
python -m pip install se-eli-mcp
python -m se_eli_mcp
```

`pip.exe` is blocked for the same reason, so install with `python -m pip`, not
`pip install`. If `python` is not on PATH, use the Windows launcher: `py -3 -m se_eli_mcp`.

```json
{ "mcpServers": { "se-eli-mcp": { "command": "python", "args": ["-m", "se_eli_mcp"] } } }
```

Do not turn Smart App Control off to work around this - it cannot be re-enabled
without reinstalling Windows.

Building from source: see [Install](#install).

An MCP server for **Swedish statutes (SFS, Svensk författningssamling)**, served as open data
by the **Riksdagen** (parliament) at `data.riksdagen.se` (keyless). It gives an AI agent the
**consolidated** text of an act with a verifiable citation: a persistent identifier, a
human-readable citation, and a link to the official source.

Part of the **eu-legal-mcp** line by [MateMatic](https://matematic.co) — one connector per EU
member state, the same citation contract everywhere.

> **On ELI.** Sweden does **not** publish native ELI (`/eli/`) URIs. To keep the line's
> contract honest, `eli_uri` carries the official persistent document identifier instead — the
> `data.riksdagen.se/dokument` URI (e.g. `https://data.riksdagen.se/dokument/sfs-2018-218`).
> The SFS number (`2018:218`) is the canonical Swedish citation. The connector never fabricates
> an `/eli/` URI and says so in its tool instructions. See `DISCOVERY.md`.

## Tools

| Tool | What it does |
|---|---|
| `se_search(query)` | Free-text search over SFS statutes (title and full text). Returns acts, each with the citation contract. |
| `se_get_act(sfs_number)` | Metadata for one act by its SFS number (e.g. `2018:218`) — title, authority, date, consolidation marker. |
| `se_get_text(sfs_number)` | The full consolidated plain text of one act. |
| `se_coverage()` | Declare what this connector covers, when each family was captured, and - explicitly - what it does NOT cover. Every gap carries a fallback. |

Every response carries the **citation contract**:

- `eli_uri` — the official persistent identifier (document URI; see the ELI note above).
- `human_readable_citation` — the act title, which embeds the SFS number, e.g. *Lag (2018:218) med kompletterande bestämmelser till EU:s dataskyddsförordning*.
- `source_url` — the browsable `data.riksdagen.se` page for the act.
- `consolidated_through` — the last amendment folded into the text (the "ändrad t.o.m." marker).

## Install

```bash
pip install -e ".[dev]"
```

Register it with your MCP client (see `.mcp.json.example`):

```json
{
  "mcpServers": {
    "se-eli-mcp": {
      "command": "se-eli-mcp",
      "env": {
        "SE_ELI_BASE_URL": "https://data.riksdagen.se",
        "SE_ELI_CACHE_DIR": "~/.matematic/cache/se-eli",
        "SE_ELI_AUDIT_DIR": "~/.matematic/audit"
      }
    }
  }
}
```

## Design

- **Public data only.** Read-only against the keyless Riksdagen open-data API; nothing is sent
  beyond the query / SFS number.
- **Audit log.** Every call appends one JSON line to `~/.matematic/audit/se-eli-mcp.jsonl`
  (AI Act art. 12 record-keeping).
- **Vendor-neutral.** No LLM provider, no telemetry; own backoff + on-disk cache.
- **No fabrication.** Identifiers and titles are parsed from the source record. If Riksdagen's
  schema changes, the connector fails loudly rather than returning stale or invented data.

See `CONSTITUTION.md` (the 4 principles) and `DISCOVERY.md` (how the source was mapped).

## Tests

```bash
pytest tests/test_instructions_drift.py tests/test_parse.py   # offline
pytest tests/test_smoke.py                                     # live Riksdagen API
```

## Licence

Apache-2.0. The Swedish legislation served is official public data of the Kingdom of Sweden;
this connector adds no rights over it.
