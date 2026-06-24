# Constitution of se-eli-mcp

Version: 0.1.0
Date: 2026-06-24
Licence: Apache-2.0

`se-eli-mcp` is an MCP server for Swedish statutes (SFS, Svensk författningssamling), served
as open data by the Riksdagen (parliament) at `data.riksdagen.se`. It fetches the consolidated
text of an act with a verifiable citation. The MVP covers statutes (doktyp=SFS); case law is a
later feature.

The 4 principles below are inherited from the `eu-legal-mcp` line Constitution (Article IV).

---

## Art. 1. Public data only

The Riksdagen open-data API is the official, public source of Swedish legislation (keyless Open
Government Data). The server is read-only and sends nothing beyond the search terms / SFS
number.

## Art. 2. Mandatory audit log

Every tool call MUST append one JSON line to `~/.matematic/audit/se-eli-mcp.jsonl`
(ts / tool / input_hash SHA-256 / output_count_or_size / duration_ms / status). Inability to
write = the tool returns an error, it does not silently skip.

## Art. 3. Vendor neutrality

No tool hardcodes an LLM provider, assumes a model, or adds commercial telemetry. The server
talks only to `data.riksdagen.se` and the local filesystem. Authentication: none; own backoff
+ cache.

## Art. 4. A persistent identifier and a human-readable citation are mandatory

Every response MUST carry three fields:
- `eli_uri`: the official persistent identifier of the act. **Sweden does not publish native
  ELI (`/eli/`) URIs**, so this field carries the equivalent stable identifier - the
  `data.riksdagen.se/dokument` document URI (e.g.
  `https://data.riksdagen.se/dokument/sfs-2018-218`). It is derived from the source record,
  never fabricated.
- `human_readable_citation`: the act title, which by Swedish convention embeds the SFS number
  (e.g. "Lag (2018:218) med kompletterande bestämmelser till EU:s dataskyddsförordning").
- `source_url`: the browsable `data.riksdagen.se` page for the act.

---

## Open points

1. **Native ELI** - if/when Sweden exposes `/eli/` URIs, `eli_uri` should switch to them and
   the document URI should move to a dedicated field.
2. **Consolidation marker** - `consolidated_through` reports the last folded-in amendment (the
   "ändrad t.o.m." marker) so the caller knows the version returned.
3. **Case law** (domstolar / vägledande avgöranden) - a separate tool family, later.

## Evolution of the constitution

Changes to art. 1-4 follow SEMVER + an entry in `CHANGELOG.md` + a `pyproject.toml` bump.

First version: 2026-06-24. Author: Wieslaw Mazur / MateMatic.
