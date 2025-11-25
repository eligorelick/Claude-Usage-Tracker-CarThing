#!/bin/sh
# Fetches usage data from Windows PC every 60 seconds
while true; do
    curl -s "http://172.16.42.1:8080/" > /tmp/usage.json 2>/dev/null
    sleep 60
done
