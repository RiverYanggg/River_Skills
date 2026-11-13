#!/usr/bin/env bash
# 只读检查：服务器上的反向隧道、SSH 别名和 Mac 命令执行是否可用。
# 用法（服务器终端）：
#   bash check-mac-tunnel.sh [ssh-alias] [tunnel-port]
# 默认别名 mac-tunnel，默认端口 2222。不修改任何配置，也不写入 Mac。
set -u

ALIAS="${1:-mac-tunnel}"
PORT="${2:-2222}"
FAIL=0

say() { printf '%s\n' "$*"; }

say "== 1. 服务器端隧道监听 (127.0.0.1:${PORT})"
if (ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null) | grep -qE "127\.0\.0\.1:${PORT}[[:space:]]"; then
  say "OK: 端口 ${PORT} 正在本机回环监听"
else
  say "FAIL: 端口 ${PORT} 没有监听。请在 Mac 终端保持运行：ssh -R ${PORT}:localhost:22 <服务器别名>"
  FAIL=1
fi

say "== 2. SSH 别名 (${ALIAS}) 是否已配置"
# ssh -G 对任意名字都会返回配置，所以必须直接检查 Host 条目是否存在
if grep -Eqi "^[[:space:]]*Host[[:space:]]+([^#]*[[:space:]])?${ALIAS}([[:space:]]|$)" "${HOME}/.ssh/config" 2>/dev/null; then
  CFG=$(ssh -G "${ALIAS}" 2>/dev/null)
  say "OK: $(printf '%s\n' "${CFG}" | awk '/^hostname /{h=$2} /^port /{p=$2} /^user /{u=$2} END{printf "hostname=%s port=%s user=%s", h, p, u}')"
else
  say "FAIL: ~/.ssh/config 中没有 Host ${ALIAS} 条目（参考 references/setup.md 添加）"
  FAIL=1
fi

say "== 3. 免密登录并在 Mac 上执行只读命令"
if OUT=$(timeout 30 ssh -o BatchMode=yes -o ConnectTimeout=15 "${ALIAS}" 'whoami; echo "$HOME"; uname -s' 2>&1); then
  say "OK:"
  say "${OUT}" | sed 's/^/    /'
else
  say "FAIL: ${OUT}"
  case "${OUT}" in
    *"Connection reset"*|*"Connection refused"*)
      say "提示：TCP 能连但握手被断开，多为 Mac 端 sshd 未运行或隧道会话已断开；在 Mac 上检查：sudo systemsetup -getremotelogin" ;;
    *"Permission denied"*)
      say "提示：公钥未加入 Mac 的 ~/.ssh/authorized_keys，或用户名错误" ;;
  esac
  FAIL=1
fi

if [ "${FAIL}" -eq 0 ]; then
  say "RESULT: PASS"
else
  say "RESULT: FAIL（按上面的提示逐项排查）"
fi
exit "${FAIL}"
