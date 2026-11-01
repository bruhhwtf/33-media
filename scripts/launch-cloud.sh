#!/usr/bin/env bash
set -euo pipefail
cd /workspace/33-media
export CUTLAB_PYTHON="$PWD/.venv/bin/python"
if [[ -n "${DISPLAY:-}" ]]; then exec npm run desktop; fi
# An isolated local test display; never exposes a web preview.
job_dir=$(mktemp -d /tmp/cutlab-display.XXXXXX)
cat > "$job_dir/xorg.conf" <<'XORG'
Section "ServerFlags"
 Option "AutoAddDevices" "false"
 Option "DontVTSwitch" "true"
EndSection
Section "Device"
 Identifier "Dummy"
 Driver "dummy"
 VideoRam 256000
EndSection
Section "Monitor"
 Identifier "Monitor"
 HorizSync 5.0 - 1000.0
 VertRefresh 5.0 - 200.0
 Modeline "1440x940" 110.00 1440 1488 1520 1600 940 943 953 980
EndSection
Section "Screen"
 Identifier "Screen"
 Device "Dummy"
 Monitor "Monitor"
 DefaultDepth 24
 SubSection "Display"
  Depth 24
  Modes "1440x940"
 EndSubSection
EndSection
XORG
/usr/lib/xorg/Xorg -displayfd 3 -config "$job_dir/xorg.conf" -logfile "$job_dir/xorg.log" -noreset -nolisten tcp 3>"$job_dir/display" >"$job_dir/stdout.log" 2>&1 &
xorg_pid=$!
trap 'kill "$xorg_pid" 2>/dev/null || true; rm -rf "$job_dir"' EXIT
for _ in {1..100}; do
 [[ -s "$job_dir/display" ]] && break
 kill -0 "$xorg_pid" 2>/dev/null || { cat "$job_dir/stdout.log"; exit 1; }
 sleep .1
done
[[ -s "$job_dir/display" ]] || { cat "$job_dir/stdout.log"; exit 1; }
export DISPLAY=":$(cat "$job_dir/display")"
if [[ "${1:-}" == "--test" ]]; then npm run test:desktop; else npm run desktop; fi
