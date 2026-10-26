# Source from ~/.bashrc after setting proxy environment variables.
# Optional: MIHOMO_PROXY_URL, MIHOMO_EXPECTED_COUNTRY (empty accepts any country).
proxycheck() {
    local proxy="${MIHOMO_PROXY_URL:-${https_proxy:-http://127.0.0.1:7890}}"
    local expected="${MIHOMO_EXPECTED_COUNTRY-}" body country attempt
    for attempt in 1 2 3; do
        country=""
        if body=$(curl -fsS --proxy "$proxy" --noproxy "" \
            --connect-timeout 3 --max-time 5 \
            https://www.cloudflare.com/cdn-cgi/trace 2>/dev/null); then
            country=$(printf '%s\n' "$body" | sed -n 's/^loc=//p')
        fi
        country=${country//$'\r'/}
        case "$country" in
            [A-Z][A-Z])
                if [ -z "$expected" ] || [ "$country" = "$expected" ]; then
                    printf '代理已开启，出口: %s ✓\n' "$country"
                    return 0
                fi
                printf '⚠ 代理已连通，出口: %s（期望 %s）\n' "$country" "$expected" >&2
                return 1
                ;;
        esac
        if [ "$attempt" -lt 3 ]; then
            printf '代理检查第 %s 次未通过，重试...\n' "$attempt" >&2
        fi
    done
    printf '⚠ 代理不可用或出口检测超时\n' >&2
    printf '可检查服务：systemctl --user status mihomo.service\n' >&2
    return 1
}

if [[ $- == *i* ]]; then
    proxycheck || :
fi
