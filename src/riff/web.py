"""Fetch a URL and extract a Document: an HTML page's article body, or a downloaded .pptx / .docx."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from riff import __version__
from riff.extract import Document, extract_docx, extract_html, extract_pptx

_MAX_BYTES = 25_000_000
_TIMEOUT = 30
_HTML_TYPES = ("text/html", "application/xhtml+xml")
_OFFICE_TYPES = {
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}
_OFFICE_SUFFIXES = (".pptx", ".docx")


def is_url(arg: str) -> bool:
    return re.match(r"https?://", arg, re.IGNORECASE) is not None


def _office_suffix(url: str, ctype: str) -> str | None:
    """The Office format of a response, or None. Hosts often serve these as octet-stream, so check the URL path too."""
    if ctype in _OFFICE_TYPES:
        return _OFFICE_TYPES[ctype]
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in _OFFICE_SUFFIXES and ctype in ("application/octet-stream", "binary/octet-stream", "application/zip"):
        return suffix
    return None


def fetch(url: str) -> tuple[str | None, bytes, str]:
    """GET `url`. Returns (office suffix or None for HTML, body bytes, charset).

    Raises ValueError for network errors, oversized bodies, and responses that are neither HTML nor .pptx/.docx.
    """
    accept = "text/html,application/xhtml+xml,application/vnd.openxmlformats-officedocument.*"
    req = Request(url, headers={"User-Agent": f"riff-lint/{__version__}", "Accept": accept})
    try:
        with urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 - scheme is restricted to http(s) by is_url
            ctype = resp.headers.get_content_type()
            suffix = _office_suffix(resp.url, ctype)
            if suffix is None and ctype not in _HTML_TYPES:
                raise ValueError(f"{url}: expected an HTML page or a .pptx/.docx file, got {ctype}")
            raw = resp.read(_MAX_BYTES + 1)
            charset = resp.headers.get_content_charset() or "utf-8"
    except HTTPError as exc:
        raise ValueError(f"{url}: HTTP {exc.code} {exc.reason}") from exc
    except URLError as exc:
        raise ValueError(f"{url}: could not fetch ({exc.reason})") from exc
    if len(raw) > _MAX_BYTES:
        raise ValueError(f"{url}: response is larger than {_MAX_BYTES // 1_000_000} MB")
    return suffix, raw, charset


def extract_url(url: str) -> Document:
    suffix, raw, charset = fetch(url)
    if suffix is None:
        return extract_html(raw.decode(charset, errors="replace"), url, main_content=True)
    # python-docx and python-pptx read from a path; the temp file only lives for the extraction.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"download{suffix}"
        path.write_bytes(raw)
        try:
            doc = extract_pptx(path) if suffix == ".pptx" else extract_docx(path)
        except Exception as exc:  # noqa: BLE001 - python-pptx/docx raise assorted types for a bad package
            raise ValueError(f"{url}: could not read as {suffix} ({type(exc).__name__}: {exc})") from exc
    doc.path = url
    return doc
