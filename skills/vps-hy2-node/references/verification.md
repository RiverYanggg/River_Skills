# 验证和维护

## 分层验收

1. 服务器：`systemctl is-enabled`、`systemctl is-active`、`ss -lunp`，确认 UDP 端口和证书状态。
2. 客户端：导入 YAML 后实际请求 `https://api.ipify.org`、`https://ipinfo.io/json` 和一个普通 HTTPS 站点；记录 HTTP 状态、耗时和出口 IP。
3. 日志：

```sh
sudo journalctl -u hysteria-server -f
sudo systemctl status hysteria-server --no-pager
sudo ss -lunp | grep ':443'
```

不要把完整认证配置、密码或订阅链接贴进报告。连接超时只能说明当前链路失败；结合服务端日志、不同网络和实际请求判断是客户端、端口、防火墙还是运营商路径问题。

## 维护

- 配置变更前复制 `/etc/hysteria/` 并保留最近一次可用版本。
- 证书续期失败先检查 TCP 80、DNS A 记录和 ACME 日志。
- 升级后重复配置校验、服务状态和真实出口测试。
- 本案例实测：移动网络不可用，电信和联通可用；该结论属于当前 VPS/IP 的运营商线路记录。
