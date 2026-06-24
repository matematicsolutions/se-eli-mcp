"""Pydantic v2 models for the Swedish Riksdagen SFS API + se-eli-mcp."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

DATASET_NOTE = (
    "SFS (Svensk forfattningssamling) is the official collection of Swedish statutes, served "
    "as open data by the Riksdagen (parliament) at data.riksdagen.se. Riksdagen publishes the "
    "consolidated text of each act (amendments incorporated up to the 'andrad t.o.m.' marker). "
    "Sweden does NOT publish native ELI (/eli/) URIs - eli_uri carries the official persistent "
    "document identifier (the data.riksdagen.se/dokument URI) and the SFS number is the "
    "canonical citation. This MVP covers statutes (doktyp=SFS); case law is not covered here."
)


class _Tolerant(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class SfsAct(_Tolerant):
    """A Swedish statute (SFS), parsed from a Riksdagen document record."""

    dok_id: str | None = None
    sfs_number: str | None = None
    title: str | None = None
    year: str | None = None
    authority: str | None = None
    date_issued: str | None = None
    consolidated_through: str | None = None

    # Citation contract (Art. 4 CONSTITUTION).
    eli_uri: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None

    # Internal: fetchable plain-text location (used by se_get_text).
    text_url: str | None = None


class SearchResult(_Tolerant):
    """Result of ``se_search``."""

    query: str
    total_matched: int
    returned: int
    items: list[SfsAct] = Field(default_factory=list)
    dataset_note: str = DATASET_NOTE


class LawText(_Tolerant):
    """Result of ``se_get_text`` (full consolidated plain text)."""

    dok_id: str
    sfs_number: str | None = None
    eli_uri: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None
    text_url: str | None = None
    consolidated_through: str | None = None
    format: str = "sfs-plain-text"
    content: str | None = None
    byte_size: int | None = None
    dataset_note: str = DATASET_NOTE
