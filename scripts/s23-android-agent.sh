#!/system/bin/sh
# Fixed read-only Android sources. No root, no remote command endpoint.
DATA=/sdcard/Download/s23-observatory-agent
SCRIPT=/data/local/tmp/s23-android-agent.sh
PIDFILE=/data/local/tmp/s23-android-agent.pid
if [ "$1" = --start ]; then
    if [ -r "$PIDFILE" ]; then
        read -r pid < "$PIDFILE"
        case "$pid" in ''|*[!0-9]*) ;; *)
            if kill -0 "$pid" 2>/dev/null && grep -F -q "$SCRIPT" "/proc/$pid/cmdline"; then
                echo AGENT_ALREADY_ACTIVE; exit 0
            fi;; esac
    fi
    /system/bin/toybox nohup /system/bin/setsid /system/bin/sh "$SCRIPT" --run </dev/null >/dev/null 2>&1 &
    exit 0
fi
[ "$1" = --run ] || exit 2
echo "$$" > "$PIDFILE"
mkdir -p "$DATA" || exit 3
TMP="$DATA/.sample-$$"
trap 'rm -f "$TMP" "$PIDFILE"; exit' TERM INT HUP
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
