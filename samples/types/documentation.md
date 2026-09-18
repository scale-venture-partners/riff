# Configuring the cache

To enable the cache, set `CACHE_URL` in your environment and restart the service. If the variable is missing, the service starts with the cache disabled and logs a warning.

To clear the cache, run `svc cache clear`. This removes all entries but does not affect stored data. The cache warms on the next request.
