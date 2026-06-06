#!/bin/bash
# scripts/healthcheck.sh
# Used by Docker HEALTHCHECK to verify the app is running.
# Returns exit code 0 (healthy) or 1 (unhealthy).

HEALTH_URL="http://localhost:${PORT:-8000}/health"

response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_URL")

if [ "$response" = "200" ]; then
    exit 0
else
    echo "Health check failed: HTTP $response"
    exit 1
fi