# Deployment notes

The service reads its config from environment variables at startup. If a
required variable is missing, it exits with a clear error rather than
falling back to a default.

We deploy on Fridays only when the on-call engineer approves. Rollbacks
run the previous image tag and take about two minutes.
