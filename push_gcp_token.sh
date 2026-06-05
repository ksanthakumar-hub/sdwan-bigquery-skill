#!/bin/bash
# Push your local GCP token to the dashboard proxy on the server.
# Run this whenever the dashboard shows "no GCP token" errors.
# Token is valid ~1 hour; run again to refresh.

set -e
TOKEN=$(gcloud auth application-default print-access-token)
echo -n "$TOKEN" | curl -s -X POST http://10.9.224.231:8082/push_token \
  --data-binary @- \
  -H "Content-Type: text/plain"
echo ""
echo "Token pushed. Dashboard will refresh automatically."
