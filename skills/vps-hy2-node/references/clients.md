# 客户端 YAML 与导入

## Mihomo/Clash Meta 示例

这是结构模板，真实交付文件必须替换所有占位符，不得把模板直接给用户导入：

```yaml
proxies:
  - name: VPS-Hy2
    type: hysteria2
    server: <VPS_OR_DOMAIN>
    port: 443
    password: <HY2_PASSWORD>
    sni: <DOMAIN>
    skip-cert-verify: false
    udp: true

proxy-groups:
  - name: Proxy
    type: select
    proxies:
      - VPS-Hy2
      - DIRECT

rules:
  - MATCH,Proxy
```

生成后用目标内核的配置测试命令验证 YAML，例如 `mihomo -t -f hy2.yaml`；Mihomo 的字段以[当前版本文档](https://wiki.metacubex.one/config/proxies/hysteria2/)为准，不随意加入 sing-box 专属字段。上述模板为节点、代理组与规则最小结构；DNS、TUN、监听和规则应结合用户现有配置，不能覆盖整个已有订阅。需要独立配置时可用回环监听的 `mixed-port: 7890`，但先检查冲突。

Karing 的配置转换不等于原生支持全部 Mihomo 全局字段。交付前从 [Karing 官方仓库](https://github.com/KaringX/karing) 对照实际版本，核对 Hy2 解析字段，尤其 SNI、证书校验、混淆和端口；无法运行手机 App 验证时明确标为待用户验证。不要声称 `proxy-groups`、`rules`、DNS、TUN 等会原样保留，App 中的路由/DNS/VPN 设置写入说明。此 Skill 不提供另一种 JSON 或 TXT 节点格式代替用户要求的 YAML。

## 导入步骤

- Clash Verge Rev：Profiles/配置文件 → 导入本地 YAML → 选择配置 → 选择 `Proxy` 组中的 Hy2 节点；TUN 只在用户需要全局接管时开启。
- FlClash：配置文件 → 从文件导入 YAML → 选择配置和节点；先关闭 Fake-IP 或改为 Redir-Host 仅用于排除 DNS 变量，确认后再按需要恢复。
- Karing：从文件导入 YAML，确认其版本支持 `hysteria2`；若 TLS SNI、证书校验、UDP 或 DNS 模式在 App 中有单独开关，按服务端实际值设置。不要把不支持的字段硬塞进 YAML。

交付时另附 `导入说明.txt`，写明文件路径、节点名、选择组、测试网址和需要在 App 内设置的项目。配置文件权限设为 600。

需要把远端文件带回本地时，在本地执行 `scp -P <SSH_PORT> <USER>@<VPS>:<REMOTE_PRIVATE_PATH> ./hy2.yaml`，再设置权限。确认本地文件存在后再说“已保存到电脑”；写到 VPS 或 Agent 容器不等于已传到用户电脑。导入后确认当前启用的是新配置而不是旧订阅；临时调用内核 API 加载不等于持久导入 GUI，重启软件后也应复核。
