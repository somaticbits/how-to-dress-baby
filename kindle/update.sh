#!/bin/sh
# Hardened local replacement for the upstream one-shot download.
cd "$(dirname "$0")" || exit 1
. ./config.sh
. ./utils.sh
is_userstore_available || exit 1

finish() {
    rm -f "$TMPFILE"
    rm -f /tmp/baby-download-error.log
    flush_temp_logs force
}
trap finish EXIT
power_status=$(/usr/bin/powerd_test -s)
level=$(printf '%s\n' "$power_status" | awk -F: '
    /Battery Level/ { gsub(/[^0-9]/, "", $2); print $2; exit }
')
charging=$(printf '%s\n' "$power_status" | awk -F: '
    /^[[:space:]]*Charging/ { gsub(/[[:space:]]/, "", $2); print $2; exit }
')
case "$IMAGE_URI" in *\?*) separator='&' ;; *) separator='?' ;; esac
url="$IMAGE_URI"
case "$level" in
    ''|*[!0-9]*) ;;
    *)
        if [ "$level" -le 100 ]; then
            url="$url${separator}batteryLevel=$level"
            case "$charging" in
                Yes|yes|No|no) url="$url&isCharging=$charging" ;;
            esac
        fi
        ;;
esac
logger "Downloading $IMAGE_URI (battery: ${level:-unknown}%, charging: ${charging:-unknown})"
logger "WiFi connection state: $(lipc-get-prop com.lab126.wifid cmState)"
logger "WiFi enabled: $(lipc-get-prop com.lab126.cmd wirelessEnable)"
if ! wget -T 20 -t 1 "$url" -O "$TMPFILE" 2> /tmp/baby-download-error.log; then
    logger "Download failed; keeping previous screensaver"
    while IFS= read -r line; do
        logger "wget: $line"
    done < /tmp/baby-download-error.log
    exit 1
fi

# Verify PNG signature, IHDR and exact 600x800 dimensions before replacement.
header=$(od -An -tx1 -N24 "$TMPFILE" | tr -d ' \n')
if [ "$header" != "89504e470d0a1a0a0000000d494844520000025800000320" ]; then
    logger "Invalid PNG or dimensions; keeping previous screensaver"
    exit 1
fi
is_userstore_available || exit 1
stage="$SCREENSAVERFILE.download"
if ! cp "$TMPFILE" "$stage"; then
    logger "Could not stage image; keeping previous screensaver"
    exit 1
fi
if ! mv "$stage" "$SCREENSAVERFILE"; then
    logger "Could not replace screensaver"
    exit 1
fi
logger "Screen saver image updated successfully (600x800 PNG)"
status=$(lipc-get-prop com.lab126.powerd status)
case "$status" in
    *Ready*|*"Screen Saver"*) eips -f -g "$SCREENSAVERFILE" ;;
esac
exit 0
