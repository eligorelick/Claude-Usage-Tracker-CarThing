#!/bin/sh
# Serves usage JSON on port 8080 for the HTML display
while true; do
    { 
        read request
        echo -e "HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: *\r\nContent-Type: application/json\r\nConnection: close\r\n"
        cat /tmp/usage.json 2>/dev/null || echo '{"error":"no data"}'
    } | nc -l -p 8080
done
