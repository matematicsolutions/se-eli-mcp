# DISCOVERY - Sweden (SFS via Riksdagen open data)

Date: 2026-06-24. Status: **BUILD** (3-tool grounding MVP shipped).

## Source

Sweden publishes its statutes as **SFS** (Svensk författningssamling). The **Riksdagen**
(parliament) exposes them through a mature, keyless **open-data API** at `data.riksdagen.se`,
in JSON / XML / HTML / plain text. Riksdagen serves the **consolidated** text of each act
(amendments folded in up to the "ändrad t.o.m. SFS YYYY:N" marker).

- **Search**: `GET /dokumentlista/?sok=<query>&doktyp=SFS&utformat=json&sz=<n>` →
  `{ dokumentlista: { "@traffar": "<total>", dokument: [ ... ] } }`.
- **Metadata**: `GET /dokumentstatus/<dok_id>.json` →
  `{ dokumentstatus: { dokument: { dok_id, beteckning, rm, organ, datum, titel, subtitel, ... } } }`.
- **Full text**: `GET /dokument/<dok_id>.text` (plain text; `.html` and `.json` also exist).

## Identifiers

- **SFS number** (`beteckning`) — `YYYY:N`, e.g. `2018:218`. This is the canonical Swedish
  citation ("SFS 2018:218"); the act title already embeds it.
- **dok_id** — `sfs-YYYY-N`, derived from the SFS number. The bare document URI
  `https://data.riksdagen.se/dokument/<dok_id>` resolves (HTTP 200).

## Record fields (search stub / status)

```
dok_id            sfs-2018-218
beteckning        2018:218
rm                2018
nummer            218
organ             Justitiedepartementet L6
datum             2018-04-19
titel             Lag (2018:218) med kompletterande bestämmelser till EU:s dataskyddsförordning
subtitel/undertitel  t.o.m. SFS 2025:256        ← consolidation marker
dokument_url_text //data.riksdagen.se/dokument/sfs-2018-218.text
dokument_url_html //data.riksdagen.se/dokument/sfs-2018-218.html
```

## Citation contract (Art. IV)

| Field | Source | Example |
|---|---|---|
| `eli_uri` | document URI from `dok_id` | `https://data.riksdagen.se/dokument/sfs-2018-218` |
| `human_readable_citation` | `titel` (embeds SFS number) | `Lag (2018:218) med kompletterande bestämmelser …` |
| `source_url` | browsable HTML page | `https://data.riksdagen.se/dokument/sfs-2018-218.html` |

**ELI note (decisive).** Sweden has **not deployed native ELI (`/eli/`) URIs**. None of the
machine sources (dokumentlista, dokumentstatus, the plain-text / HTML documents) carries an
`/eli/` identifier; the official persistent identifier is the Riksdagen document URI, and the
SFS number is the canonical citation. Per the line rule "parse the ELI, never fabricate it",
`eli_uri` carries this equivalent stable identifier, stated plainly in INSTRUCTIONS, README and
CONSTITUTION (the line's "say what you don't have" freshness principle).

## Tools

- `se_search(query)` — `dokumentlista?sok=<query>&doktyp=SFS&utformat=json`, return acts.
- `se_get_act(sfs_number)` — derive `dok_id`, fetch `dokumentstatus/<dok_id>.json`, the
  citation contract + `consolidated_through`.
- `se_get_text(sfs_number)` — derive `dok_id`, fetch `dokument/<dok_id>.text` (consolidated).

## Open points

- Free-text search (title + full text); results ranked by relevance (`sort=rel`).
- `consolidated_through` parsed from the "t.o.m." subtitle so the caller knows the version.
- Case law (vägledande avgöranden) out of scope for this MVP.
