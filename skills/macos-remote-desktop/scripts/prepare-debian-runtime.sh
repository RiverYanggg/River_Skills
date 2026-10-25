#!/bin/bash
# Linux server only. Downloads packages from configured apt repositories, no sudo.
# XFCE, xauth, xdpyinfo and the required shared libraries must already be installed.
set -euo pipefail
if [[ $(uname -s) != Linux ]]; then echo 'Run on the Linux server.' >&2; exit 2; fi
for tool in apt-get dpkg-deb ldd python3; do
  command -v "$tool" >/dev/null || { echo "Missing: $tool" >&2; exit 1; }
done
desktop_data=${XDG_DATA_HOME:-$HOME/.local/share}/macos-remote-desktop
runtime_dir=$desktop_data/runtime
if [[ -e "$runtime_dir" ]]; then
  echo "Runtime already exists: $runtime_dir. Inspect/reuse it instead of overwriting." >&2
  exit 1
fi
mkdir -p "$desktop_data"
stage=$(mktemp -d "$desktop_data/.runtime-stage.XXXXXX")
cleanup() {
  # Remove only this script's unique staging directory, including failed downloads.
  python3 - "$stage" <<'PY'
import pathlib, shutil, sys
p = pathlib.Path(sys.argv[1])
if p.name.startswith('.runtime-stage.') and p.is_dir():
    shutil.rmtree(p)
PY
}
trap cleanup EXIT
mkdir -p "$stage/packages" "$stage/runtime"
cd "$stage/packages"
apt-get download tigervnc-standalone-server tigervnc-common tigervnc-tools
for package in ./*.deb; do dpkg-deb -x "$package" "$stage/runtime"; done
ldd "$stage/runtime/usr/bin/Xtigervnc" >"$stage/ldd.txt"
if grep -q 'not found' "$stage/ldd.txt"; then
  cat "$stage/ldd.txt" >&2
  echo 'Missing shared libraries; ask the administrator to install the relevant distro packages.' >&2
  exit 1
fi
test -x "$stage/runtime/usr/bin/tigervncpasswd"
mv "$stage/runtime" "$runtime_dir"
echo "Runtime prepared: $runtime_dir"
echo 'System dependencies were not installed. Re-run desktop.py configure to check them.'
