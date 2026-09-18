# v2.4.0 — 2026-03-01

## Added
- Retry with exponential backoff on transient upstream 5xx responses.
- `--timeout` flag to override the default 30-second request timeout.

## Fixed
- Duplicate entries when the same URL was submitted twice within one batch.

## Changed
- The default page size for search results is now 50, up from 20.
