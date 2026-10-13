# Optional Kindle downloader

The HA app serves images; a separate Kindle extension must download them and wake
the device. Manual USB tests covered a Kindle Basic 8th generation (KT3), firmware
5.12.5, with KUAL and NiLuJe's linkss screensaver hack. Other devices need testing.

1. Preserve existing screensavers and keep OTA updates blocked before networking.
2. Install a compatible KUAL/linkss setup using the community's device-specific
   instructions; do not update firmware merely to follow this guide.
3. Install the [online screensaver extension](https://github.com/FalconFour/onlinescreensaverPW2)
   (reviewed source commit `591223d15082cab86ba3f56f2a06a44115ea69fd`). Its own licence
   and instructions apply. It supplies `utils.sh`, scheduler and menu actions.
4. Back up its files, then copy the optional files from this repository's
   `kindle/` directory into its `bin/` directory. Configure `IMAGE_URI` with your
   actual HA LAN address: `http://YOUR_HA_LAN_IP:8000/display.png`.
5. For a manual test, change the KUAL Update now action to `bin/manual-test.sh`.
   It turns WiFi on for the download, then off. It checks storage availability,
   retains the previous image on failure, and validates PNG header/dimensions.
6. Eject and physically unplug. Restart after USB script/configuration edits.
   Test one download before enabling scheduled updates. Correct the system clock
   and verify both UTC time and the configured timezone before testing RTC wake.

The supplied configuration defaults to hourly updates and Paris DST rules. A
five-minute supervised trial showed scheduled wakes, successful image downloads
and WiFi shutoff, but is not an overnight battery-life guarantee. The upstream
scheduler's minimum wait and suspend preparation can delay exact 07:00/19:00
switching. Logging can grow: keep it for initial verification, then manage it.

At 15% or below the server adds a battery warning unless the downloader reports
charging. The warning reflects the last download, not a continuously live gauge.
Changing the server cannot wake or refresh a sleeping Kindle by itself.

## Network and update protection

The endpoint is HTTP and unauthenticated for old-device compatibility: LAN only.
If using firewall restrictions, explicitly allow the Kindle's path to HA TCP
port 8000 and associated return traffic. Subnets and UniFi zones are not
interchangeable; inspect actual routing and rule counters. A cached browser page
does not prove a downloader can connect.

For firmware 5.11+, the old `update.bin.tmp.partial` directory is not a reliable
OTA blocker. The community documents a reversible
[Rename OTA Binaries approach](https://kindlemodding.org/jailbreaking/Legacy/post-jailbreak/disable-ota.html).
Verify the renamed updater binaries on-device; USB files alone are insufficient.
This is not a guarantee against every update mechanism. LAN-only Internet
restrictions provide an additional layer, where configured correctly.
