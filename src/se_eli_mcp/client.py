"""Async httpx client for the Swedish Riksdagen open-data API with cache.

Riksdagen serves SFS statutes as open data (keyless) at ``data.riksdagen.se``:
- ``/dokumentlista/?sok=...&doktyp=SFS&utformat=json`` - search (JSON)
- ``/dokumentstatus/<dok_id>.json`` - one act's metadata (JSON)
- ``/dokument/<dok_id>.text`` - the consolidated plain text

We keep our own backoff + cache.
"""

from __future__ import annotations

import anyio
import httpx

from .cache import HttpCache

DEFAULT_BASE_URL = "https://data.riksdagen.se"
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
USER_AGENT = "se-eli-mcp/0.1.0 (+https://github.com/matematicsolutions/se-eli-mcp)"

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 3


class SeError(Exception):
    """Raised when the Riksdagen response cannot be retrieved or is invalid."""


class RiksdagenClient:
    """Async client for the Riksdagen open-data API.

    Use as ``async with RiksdagenClient() as c: ...``.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        cache: HttpCache | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._cache = cache or HttpCache()
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            follow_redirects=True,
        )

    async def __aenter__(self) -> RiksdagenClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()
        self._cache.close()

    async def _get(self, url: str, *, params: dict[str, str] | None, category: str) -> str:
        cache_key = url if not params else url + "?" + str(httpx.QueryParams(params))
        cached = self._cache.get(cache_key)
        if cached is not None and isinstance(cached, str):
            return cached
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                resp = await self._http.get(url, params=params)
                resp.raise_for_status()
                self._cache.set(cache_key, resp.text, ttl=HttpCache.ttl_for(category))
                return resp.text
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code not in _RETRY_STATUS or attempt == _MAX_ATTEMPTS - 1:
                    raise
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
            await anyio.sleep(0.5 * (2**attempt))
        assert last_exc is not None
        raise last_exc

    async def search(self, query: str, *, maximum_records: int) -> str:
        """Search SFS statutes by free text (title and full text)."""
        params = {
            "sok": query,
            "doktyp": "SFS",
            "utformat": "json",
            "sz": str(maximum_records),
            "sort": "rel",
        }
        return await self._get(f"{self.base_url}/dokumentlista/", params=params, category="search")

    async def get_status(self, dok_id: str) -> str:
        """Fetch one act's metadata (dokumentstatus JSON)."""
        return await self._get(
            f"{self.base_url}/dokumentstatus/{dok_id}.json", params=None, category="act"
        )

    async def get_text(self, dok_id: str) -> str:
        """Fetch one act's consolidated plain text."""
        return await self._get(
            f"{self.base_url}/dokument/{dok_id}.text", params=None, category="act"
        )
