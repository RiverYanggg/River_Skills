#!/bin/bash
# Run on the user's Mac, not on the Linux server. Compatible with macOS Bash 3.2.
set -euo pipefail
usage() {
  echo 'Usage: bash mac-connect.sh SSH_ALIAS [INSTANCE=mac-desktop] [LOCAL_PORT=15902]' >&2
}
if [[ $# -lt 1 || $# -gt 3 ]]; then usage; exit 2; fi
target=$1
instance=${2:-mac-desktop}
local_port=${3:-15902}
target_pattern='^[a-zA-Z0-9_][a-zA-Z0-9_.@:-]*$'
if [[ ! "$target" =~ $target_pattern ]]; then
  echo 'Use an SSH alias or user@host; configure keys/ports/jump hosts in ~/.ssh/config.' >&2
  exit 2
fi
if [[ ! "$instance" =~ ^[a-z][a-z0-9-]{0,39}$ ]]; then
  echo 'Invalid instance name.' >&2; exit 2
fi
if [[ ! "$local_port" =~ ^[1-9][0-9]{3,4}$ ]] || (( local_port > 65535 )); then
  echo 'Choose a local port between 1024 and 65535.' >&2; exit 2
fi
if (( local_port < 1024 )); then echo 'Use an unprivileged local port.' >&2; exit 2; fi
if [[ $(uname -s) != Darwin ]]; then
  echo 'This helper runs on your Mac. Deploy/configure the desktop on Linux first.' >&2
  exit 2
fi
for tool in ssh nc lsof open; do
  command -v "$tool" >/dev/null || { echo "Missing Mac command: $tool" >&2; exit 1; }
done
if lsof -nP -iTCP:"$local_port" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Local port $local_port is already occupied. Choose another port; no process was stopped." >&2
  exit 1
fi
echo "Checking and starting your Linux desktop via SSH target: $target"
ssh "$target" "~/.local/bin/$instance start"
remote_port=$(ssh "$target" "~/.local/bin/$instance port")
if [[ ! "$remote_port" =~ ^[0-9]{4,5}$ ]] || (( remote_port < 1024 || remote_port > 65535 )); then
  echo 'Invalid port returned by server. Check SSH login output and instance configuration.' >&2
  exit 1
fi
echo "VNC password, if needed: ssh $target '~/.local/bin/$instance password'"
echo "Opening local tunnel $local_port -> server localhost:$remote_port"
ssh -N -o ControlMaster=no -o ControlPath=none \
  -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -L "127.0.0.1:$local_port:127.0.0.1:$remote_port" "$target" &
tunnel_pid=$!
cleanup() {
  kill "$tunnel_pid" 2>/dev/null || true
  wait "$tunnel_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
ready=false
for attempt in {1..30}; do
  if ! kill -0 "$tunnel_pid" 2>/dev/null; then
    echo 'SSH tunnel stopped. Read the SSH error above; verify the same alias works with ssh.' >&2
    exit 1
  fi
  banner=$(nc -G 1 -w 1 127.0.0.1 "$local_port" </dev/null 2>/dev/null || true)
  if [[ "$banner" == RFB\ 003.* ]]; then ready=true; break; fi
  sleep 0.2
done
if [[ "$ready" != true ]]; then
  echo 'No RFB banner through tunnel. Check server listener and SSH forwarding policy.' >&2
  exit 1
fi
if ! kill -0 "$tunnel_pid" 2>/dev/null; then
  echo 'SSH tunnel exited during the connection check; Screen Sharing was not opened.' >&2
  exit 1
fi
open "vnc://127.0.0.1:$local_port"
echo 'Screen Sharing opened. Keep this terminal running; Ctrl+C closes this tunnel.'
wait "$tunnel_pid"
