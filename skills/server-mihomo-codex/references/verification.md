# 分层诊断与完成标准

## 验证顺序

1. **主机与进程**：核对 `hostname`、当前账号、unit 的 MainPID；systemd active、监听端口和测试请求必须在同一台服务器上。共享 HOME 的多登录节点不共享进程。
2. **配置与监听**：`mihomo -t` 成功；混合代理仅回环监听；控制接口私有。TCP 控制接口不能误写成 HTTP 代理端口。
3. **节点 bootstrap**：检查节点域名、所用 DNS、TCP/TLS 端口。系统 `getaddrinfo` 失败仅说明系统 resolver 不可用，Mihomo 使用自有 DNS 时仍可能成功。
4. **代理出口**：显式经代理请求 Cloudflare trace，核对 HTTP 成功及 `loc=`。不经代理的 curl 失败不能代表代理失败。
5. **OpenAI 路由**：检查 OpenAI 专用代理组的选中项，分别测试 auth 和 ChatGPT 域名。
6. **账户授权**：`codex login status` 成功才算已保存登录状态；真实模型请求成功才证明推理可用。网络 200 不是订阅权限证明。
7. **Shell 生命周期**：重新 SSH 交互式登录应显示出口检查；非交互 SSH/scp 不输出额外检查文字。重启/全登出持续运行若未实测则明确保留限制。

```bash
# 服务器；PORT 替换为实际端口（示例 7890）
curl -fsS --proxy http://127.0.0.1:7890 --noproxy '' \
  --connect-timeout 5 --max-time 15 https://www.cloudflare.com/cdn-cgi/trace
curl -sS --proxy http://127.0.0.1:7890 --noproxy '' \
  --connect-timeout 5 --max-time 20 -o /dev/null -w '%{http_code}\n' \
  https://auth.openai.com/.well-known/openid-configuration
curl -sS --proxy http://127.0.0.1:7890 --noproxy '' \
  --connect-timeout 5 --max-time 20 -o /dev/null -w '%{http_code}\n' \
  https://chatgpt.com/robots.txt
```

## 常见误判

| 表象 | 可支持的结论 | 下一步 |
|---|---|---|
| 所有节点的系统 DNS 都报错 | 系统解析链路异常；不能断定订阅全失效 | 保留订阅 DNS，检查 `proxy-server-nameserver`、可达 bootstrap DNS 和 Mihomo 脱敏日志 |
| 首页 403 | 收到了 HTTP 响应；不证明账号可登录，也不直接证明节点失效 | 区分网页挑战/地区/上游响应，测试 auth 和 Codex 实际路径 |
| TLS 错误或状态 000 | 尚未收到有效目标 HTTP 响应 | 检查节点 TCP、TLS、路由和 DNS，不直接归因账号 |
| Cloudflare 出口 US，但 auth 失败 | 普通代理可用，OpenAI 路由仍有问题 | 检查专用组是否仍选另一个节点 |
| 延迟 API 全失败 | 该测试 URL/超时/路径失败 | 用真实代理请求交叉验证；不要把 HTTPS 域名换成 IP 后忽略 SNI/证书差异 |
| 服务 active，curl connection refused | 端口可能尚未就绪、主机不一致或地址不匹配 | 等待端口、核对 MainPID、hostname 和监听；不直接重装 |
| journal 不可读 | 当前账号没有日志读取权限 | 使用私有文件日志或当前可用日志方式，不索取系统管理员日志权限来替代排错 |
| 超算欢迎信息说需要平台代理 | 这是网络策略线索 | 根据实际 DNS/TCP/代理测试确认；不能只凭提示宣布不能使用 Mihomo |

## DNS 排查示例

```bash
# 服务器；NODE_HOST 在私密变量/配置中读取，不公开节点地址
getent ahostsv4 "$NODE_HOST"
dig @DNS_SERVER "$NODE_HOST" A +time=2 +tries=1
```

记录结果前脱敏节点主机名、账号、密码、secret、订阅 URL。不要把凭据化域名当普通公开域名输出。公共 DNS 也可能不可达，按测得结果选择，不把某个地址永久视作通用解法。

订阅原有 DoH/bootstrap DNS 可用时，恢复它通常比重装内核更直接。测试程序本身可能有错误：例如缺依赖、文件路径未展开、TLS 证书对不上 IP，均不能算节点故障证据。

## 交付模板

- 服务器身份（用户可识别的 SSH 别名，不发布私人地址）、软件版本、配置位置。
- 代理端口和控制接口类型、选中代理组/节点、服务启停与日志命令。
- 实测出口地区、OpenAI HTTP/TLS 结果、CLI 版本、是否完成真实账号授权。
- 登录自动检查结果与 `proxycheck`；明确它最多增加约 15 秒网络等待，不自动修复服务。
- 尚未完成的真实账户/模型/跨重启验证，不用“配置完成”掩盖这些限制。
