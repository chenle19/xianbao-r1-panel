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
CONTROL_DIR=${R1_PANEL_CONTROL_DIR:-/control}
mkdir -p "$CONTROL_DIR"

set_dpms() {
  value="$1"
  connector=$(modetest -M i915 -c 2>/dev/null | awk '$3 == "connected" && $4 ~ /^DSI/ { print $1; exit }')
  [ -n "$connector" ] && modetest -M i915 -w "$connector:2:$value" >/dev/null 2>&1 || true
}

turn_off_until_reboot() {
  gpu_device=$(basename "$(readlink -f /sys/class/drm/card0/device 2>/dev/null || true)")
  case "$gpu_device" in
    ????:??:??.?) ;;
    *) return 1 ;;
  esac
  [ -e "/sys/bus/pci/drivers/i915/$gpu_device" ] || return 1
  printf '%s' "$gpu_device" > /sys/bus/pci/drivers/i915/unbind
}

while true; do
  rm -f "$CONTROL_DIR/screen_on.state"
  set_dpms 0
  printf '{"screen":"on"}\n' > "$CONTROL_DIR/screen.state"
  cog --platform=drm "$PANEL_URL" &
  COG_PID=$!
  while kill -0 "$COG_PID" 2>/dev/null; do
    if [ -f "$CONTROL_DIR/screen_off_boot.request" ]; then
      rm -f "$CONTROL_DIR/screen_off_boot.request"
      kill "$COG_PID" 2>/dev/null || true
      wait "$COG_PID" 2>/dev/null || true
      set_dpms 3
      echo '{"screen":"turning_off_until_reboot"}' > "$CONTROL_DIR/screen.state"
      if turn_off_until_reboot; then
        echo '{"screen":"off_until_reboot"}' > "$CONTROL_DIR/screen.state"
        while true; do sleep 3600; done
      fi
      echo '{"screen":"hard_off_failed"}' > "$CONTROL_DIR/screen.state"
      set_dpms 0
      break
    fi
    if [ -f "$CONTROL_DIR/screen_off.request" ]; then
      rm -f "$CONTROL_DIR/screen_off.request"
      kill "$COG_PID" 2>/dev/null || true
      wait "$COG_PID" 2>/dev/null || true
      set_dpms 3
      printf '{"screen":"off"}\n' > "$CONTROL_DIR/screen.state"
      /usr/local/bin/r1-touch-wake || true
      set_dpms 0
      printf '{"screen":"on"}\n' > "$CONTROL_DIR/screen.state"
      break
    fi
    sleep 0.15
  done
  wait "$COG_PID" 2>/dev/null || true
  sleep 0.2
done
