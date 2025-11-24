# scripts/monitor.sh
#!/bin/bash

# Simple monitoring script
# Run via cron: */5 * * * * /opt/radio-cortex/scripts/monitor.sh

HEALTH_URL="http://localhost:8000/health"
LOG_FILE="/opt/radio-cortex/logs/monitor.log"

# Check if API is responding
if curl -f $HEALTH_URL > /dev/null 2>&1; then
    echo "[$(date)] ✅ API is healthy" >> $LOG_FILE
else
    echo "[$(date)] ❌ API is DOWN!" >> $LOG_FILE
    # Send alert (email, webhook, etc.)
    # systemctl restart radio-cortex
fi