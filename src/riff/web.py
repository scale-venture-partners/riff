"""Fetch a URL and extract just its article body as a Document."""

from __future__ import annotations

import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from riff import __version__
from riff.extract import Document, extract_html

_MAX_BYTES = 10_000_000
_TIMEOUT = 30


def is_url(arg: str) -> bool:
    return re.match(r"https?://", arg, re.IGNORECASE) is not None


def fetch_html(url: str) -> str:
    """GET `url` and return decoded HTML. Raises ValueError for network errors and non-HTML responses."""
    req = Request(url, headers={"User-Agent": f"riff-lint/{__version__}", "Accept": "text/html,application/xhtml+xml"})
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 - scheme is restricted to http(s) by is_url
            ctype = resp.headers.get_content_type()
            if ctype not in ("text/html", "application/xhtml+xml"):
                raise ValueError(f"{url}: expected an HTML page, got {ctype}")
            raw = resp.read(_MAX_BYTES + 1)
            charset = resp.headers.get_content_charset() or "utf-8"
    except HTTPError as exc:
        raise ValueError(f"{url}: HTTP {exc.code} {exc.reason}") from exc
    except URLError as exc:
        raise ValueError(f"{url}: could not fetch ({exc.reason})") from exc
    if len(raw) > _MAX_BYTES:
        raise ValueError(f"{url}: page is larger than {_MAX_BYTES // 1_000_000} MB")
    return raw.decode(charset, errors="replace")


def extract_url(url: str) -> Document:
    return extract_html(fetch_html(url), url, main_content=True)
