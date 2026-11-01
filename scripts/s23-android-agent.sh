#!/system/bin/sh
# Fixed read-only Android sources. No root, no remote command endpoint.
DATA=/sdcard/Download/s23-observatory-agent
SCRIPT=/data/local/tmp/s23-android-agent.sh
PIDFILE=/data/local/tmp/s23-android-agent.pid
LOCK=/data/local/tmp/s23-android-agent.lock
active() {
    [ -r "$PIDFILE" ] || return 1
    read -r pid < "$PIDFILE"
    case "$pid" in ''|*[!0-9]*) return 1;; esac
    kill -0 "$pid" 2>/dev/null && grep -F -q "$SCRIPT" "/proc/$pid/cmdline" 2>/dev/null
}
if [ "$1" = --status ]; then
    if active; then echo AGENT_ACTIVE; exit 0; else echo AGENT_STOPPED; exit 3; fi
fi
if [ "$1" = --stop ]; then
    if active; then
        kill "$pid"
        for attempt in 1 2 3 4 5 6 7 8; do active || { echo AGENT_STOPPED; exit 0; }; sleep 1; done
        echo ERROR_STOP_TIMEOUT; exit 6
    fi
    echo AGENT_STOPPED; exit 0
fi
if [ "$1" = --start ]; then
    if active; then echo AGENT_ALREADY_ACTIVE; exit 0; fi
    /system/bin/toybox nohup /system/bin/setsid /system/bin/sh "$SCRIPT" --run </dev/null >/dev/null 2>&1 &
    for attempt in 1 2 3 4 5; do sleep 1; if active; then echo AGENT_STARTED; exit 0; fi; done
    echo ERROR_START_TIMEOUT; exit 5
fi
[ "$1" = --run ] || exit 2
if ! mkdir "$LOCK" 2>/dev/null; then
    if active; then exit 0; fi
    rmdir "$LOCK" 2>/dev/null || exit 7
    mkdir "$LOCK" 2>/dev/null || exit 7
fi
echo "$$" > "$PIDFILE"
mkdir -p "$DATA" || exit 3
TMP="$DATA/.sample-$$"
cleanup() { rm -f "$TMP" "$PIDFILE"; rmdir "$LOCK" 2>/dev/null; }
trap 'exit 0' TERM INT HUP
trap cleanup EXIT
while :; do
    read -r nonce < "$DATA/request" 2>/dev/null
    case "$nonce" in ''|*[!0-9a-f]*) sleep 5; continue;; esac
    [ "${#nonce}" -eq 32 ] || { sleep 5; continue; }
    {
        printf 'S23AGENT1 %s\n@before\n' "$nonce"
        cut -d ' ' -f 1 /proc/uptime
        echo @cpu_before
        grep '^cpu' /proc/stat
        sleep 1
        echo @after
        cut -d ' ' -f 1 /proc/uptime
        echo @cpu_after
        grep '^cpu' /proc/stat
        echo @network
        cat /proc/net/dev
        echo @load
        cat /proc/loadavg 2>/dev/null
        echo @wifi
        cmd wifi status | grep -oE 'RSSI: -?[0-9]+|, Tx Link speed: [0-9]+Mbps|, Rx Link speed: [0-9]+Mbps|Frequency: [0-9]+MHz'
        echo @battery
        dumpsys battery | grep -E '^  (AC powered|USB powered|Wireless powered|status|health|level|scale|voltage|temperature):'
    } > "$TMP" && mv -f "$TMP" "$DATA/snapshot"
    for tick in 1 2 3 4 5 6; do
        sleep 5
        read -r next < "$DATA/request" 2>/dev/null
        [ "$next" = "$nonce" ] || break
    done
done
