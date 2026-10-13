#!/bin/sh
cd "$(dirname "$0")" || exit 1
. ./config.sh
. ./utils.sh
is_userstore_available || exit 1
cleanup() {
    lipc-set-prop com.lab126.cmd wirelessEnable 0
    logger "Manual test finished; WiFi disabled"
    flush_temp_logs force
}
trap cleanup EXIT
trap 'exit 1' INT TERM
logger "Manual test started"
lipc-set-prop com.lab126.cmd wirelessEnable 1
sleep 10
sh ./update.sh
exit $?
