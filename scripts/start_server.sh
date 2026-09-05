#!/usr/bin/env bash
set -eo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
API_KEY="${API_KEY:-qwen3-direct-access}"
RESTART_INTERVAL="${RESTART_INTERVAL_SECONDS:-18000}"
HEALTH_TIMEOUT=120
RUN_SINGLE_CYCLE="${RUN_SINGLE_CYCLE:-false}"

echo "===================================================================="
echo " Starting AS Cloud SD-Turbo Supervisor (server8)"
echo " Host: $HOST | Port: $PORT"
echo " Restart Interval: ${RESTART_INTERVAL}s"
echo "===================================================================="

cleanup() {
    echo ""
    echo "Caught shutdown signal! Terminating server and tunnel..."
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill -TERM "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    if [ -n "$TUNNEL_PID" ] && kill -0 "$TUNNEL_PID" 2>/dev/null; then
        kill -TERM "$TUNNEL_PID" 2>/dev/null || true
    fi
    echo "Cleanup complete."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

setup_tunnel() {
    if ! command -v cloudflared &> /dev/null; then
        if [ "$(uname)" = "Linux" ]; then
            curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
            chmod +x cloudflared
            export PATH="$PWD:$PATH"
        fi
    fi

    if command -v cloudflared &> /dev/null; then
        echo "Starting Cloudflare Quick Tunnel on port $PORT..."
        cloudflared tunnel --url "http://127.0.0.1:$PORT" --no-autoupdate > tunnel.log 2>&1 &
        TUNNEL_PID=$!

        echo "Waiting for public tunnel URL to appear in tunnel.log..."
        PUBLIC_URL=""
        for i in $(seq 1 30); do
            sleep 1
            if grep -o "https://[-a-zA-Z0-9@:%._\+~#=]\+\.trycloudflare\.com" tunnel.log > /dev/null 2>&1; then
                PUBLIC_URL=$(grep -o "https://[-a-zA-Z0-9@:%._\+~#=]\+\.trycloudflare\.com" tunnel.log | head -n 1)
                break
            fi
        done

        if [ -n "$PUBLIC_URL" ]; then
            echo ""
            echo "===================================================================="
            echo " [SUCCESS] Public Tunnel URL: $PUBLIC_URL"
            echo "===================================================================="
            echo ""

            echo "$PUBLIC_URL" > endpoint.txt
            git config user.name "github-actions[bot]"
            git config user.email "github-actions[bot]@users.noreply.github.com"
            git add endpoint.txt
            git commit -m "chore: update live endpoint.txt [skip ci]" || true
            git push origin main || true
        else
            echo "Warning: Could not extract Quick Tunnel URL."
        fi
    fi
}

cycle_count=0

while true; do
    cycle_count=$((cycle_count + 1))
    echo "--------------------------------------------------------------------"
    echo " [Cycle #$cycle_count] Starting SD-Turbo server at $(date -u)..."
    echo "--------------------------------------------------------------------"

    python3 -m uvicorn src.server:app --host "$HOST" --port "$PORT" &
    SERVER_PID=$!

    echo "Waiting for server to report healthy at http://127.0.0.1:$PORT/health..."
    healthy=false
    for (( i=1; i<=HEALTH_TIMEOUT; i++ )); do
        if ! kill -0 "$SERVER_PID" 2>/dev/null; then
            echo "ERROR: Server process died during startup!"
            exit 1
        fi
        if response=$(curl -s "http://127.0.0.1:$PORT/health" 2>/dev/null); then
            if echo "$response" | grep -q '"status":\s*"ok"'; then
                echo "Server reports HEALTHY! Response: $response"
                healthy=true
                break
            fi
        fi
        sleep 2
    done

    if [ "$healthy" = false ]; then
        echo "ERROR: Server failed to report healthy within timeout."
        kill -9 "$SERVER_PID" 2>/dev/null || true
        exit 1
    fi

    if [ -z "$TUNNEL_PID" ] || ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
        setup_tunnel
    fi

    echo "Running self-test image generation..."
    TEST_RES=$(curl -s -X POST "http://127.0.0.1:$PORT/v1/images/generations" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $API_KEY" \
        -d '{"prompt":"test sphere","size":"256x256"}' || true)
    echo "Self-test result completed."

    echo "Serving image requests for $RESTART_INTERVAL seconds (~$(( RESTART_INTERVAL / 3600 )) hours)..."
    elapsed=0
    interval_step=10
    while [ "$elapsed" -lt "$RESTART_INTERVAL" ]; do
        if ! kill -0 "$SERVER_PID" 2>/dev/null; then
            echo "WARNING: Server process died unexpectedly at elapsed=${elapsed}s!"
            break
        fi
        sleep "$interval_step"
        elapsed=$((elapsed + interval_step))
    done

    echo "Reached scheduled restart threshold. Gracefully stopping..."
    kill -TERM "$SERVER_PID" 2>/dev/null || true
    sleep 5
    if kill -0 "$SERVER_PID" 2>/dev/null; then
        kill -9 "$SERVER_PID" 2>/dev/null || true
    fi

    if [ "$RUN_SINGLE_CYCLE" = "true" ]; then
        break
    fi
    sleep 5
done
