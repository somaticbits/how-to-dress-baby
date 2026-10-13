# LAN Home Assistant endpoint; the Mac is no longer needed for image downloads.
# POSIX timezone: Paris, including last-Sunday March/October DST transitions.
export TZ='CET-1CEST,M3.5.0/2,M10.5.0/3'
DEFAULTINTERVAL=60
SCHEDULE="00:00-07:00=60 07:00-19:00=60 19:00-24:00=60"
IMAGE_URI="http://192.168.1.100:8000/display.png"
SCREENSAVERFOLDER=/mnt/us/linkss/screensavers
SCREENSAVERFILE=$SCREENSAVERFOLDER/bg_ss00.png
LOGGING=1
LOGFILE=/mnt/us/extensions/onlinescreensaver/log/onlinescreensaver.log
TMPFILE=/tmp/tmp.onlinescreensaver.png
