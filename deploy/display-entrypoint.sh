#!/bin/sh
set -eu
export WPE_DISABLE_SANDBOX=1
PANEL_URL=${PANEL_URL:-http://127.0.0.1:8080}
if [ "${R1_LOAD_TOUCH:-true}" = "true" ]; then
  OUT=/opt/r1-touch
  load_module() {
    name="$1"
    path="$2"
    lsmod | awk '{print $1}' | grep -qx "$name" || insmod "$path" || true
  }
  load_module pinctrl_intel "$OUT/pinctrl-intel.ko"
  load_module pinctrl_alderlake "$OUT/pinctrl-alderlake.ko"
  load_module intel_lpss "$OUT/intel-lpss.ko"
  load_module intel_lpss_pci "$OUT/intel-lpss-pci.ko"
  load_module hid /host-lib-modules/hid.ko
  load_module hid_generic /host-lib-modules/hid-generic.ko
  load_module i2c_hid "$OUT/i2c-hid-hantick-poll.ko"
  load_module hid_multitouch "$OUT/hid-multitouch-hantick.ko"
  load_module evdev /host-lib-modules/evdev.ko
fi
chvt 1 >/dev/null 2>&1 || true
exec cog --platform=drm "$PANEL_URL"
