# 服务端部署参考

## 购买 VPS 与交付信息

先确认机房位置、KVM 虚拟化、公网 IPv4、允许 UDP、月流量和续费价格，而不是只看 CPU。购买由用户在商家官网完成支付，Agent 不代填银行卡。保存商家控制台入口和订单信息到私密位置，等待邮件提供 IP、SSH 端口和登录方式。

本案例购买 RackNerd 的 2 GB KVM VPS Special：2 vCPU、35 GB SSD、2 GB RAM、5000 GB Monthly Premium Bandwidth、1 Gbps 网口，购买时广告价 $35.99/年。这些是历史订单规格，不代表当前售价。5000 GB 是每月流量额度，1 Gbps 是端口速率；流量统计方向、重置日期和超额政策以当前商家控制台及条款为准。购买前可询问测试 IP/试用或退款条件，先验证本地运营商路径；不要承诺换商家或机房必定可用。

以下命令中的 `<VPS>`、`<USER>`、`<DOMAIN>`、`<HY2_PASSWORD>` 都是占位符，执行前替换为用户实际值；密码不要出现在 shell 历史或提交内容中，优先使用交互式读取。

## 1. 探测与备份

```sh
# 本地 Mac/Windows 的 SSH 客户端
ssh -p <SSH_PORT> <USER>@<VPS>

# VPS 内
cat /etc/os-release
uname -m
free -h
df -h
sudo ss -lntup
sudo systemctl list-units --type=service --state=running
```

备份 `/etc/hysteria/`、防火墙规则和将修改的 systemd 单元。不要停止 SSH；只开放实际使用的 Hy2 UDP 端口（常用 443，若冲突先换端口）。

## 2. 域名和证书

优先使用用户自己的域名并添加 A 记录指向 VPS。没有域名时可用 `192-0-2-1.sslip.io` 形式的主机名替换为真实地址对应的 sslip.io 名称。ACME HTTP-01 需要公网 TCP 80 可达；证书名称必须与客户端 `sni` 一致。证书验证保持开启，不用 `insecure: true` 代替证书。

## 3. Hysteria 2

官方资料：

- [官方安装说明](https://v2.hysteria.network/docs/getting-started/Installation/)
- [官方安装脚本](https://v2.hysteria.network/docs/getting-started/Server-Installation-Script/)
- [完整服务端配置](https://v2.hysteria.network/docs/advanced/Full-Server-Config/)

安装时读取当前文档，核对下载来源和架构；如使用官方脚本，先下载到临时文件审阅，再在 VPS 执行，不使用第三方一键面板代替官方流程。默认配置路径通常为 `/etc/hysteria/config.yaml`，但必须以安装输出和 `systemctl cat hysteria-server` 为准。不要假设所有版本都有独立的配置检查子命令，先看 `hysteria --help` 与实际二进制的帮助。

按照官方安装方式获取与系统架构匹配的 `hysteria-server`，使用官方文档的 YAML 配置格式。核心配置应包含：

```yaml
listen: :443
acme:
  domains:
    - <DOMAIN>
  email: <CONTACT_EMAIL>
auth:
  type: password
  password: <HY2_PASSWORD>
masquerade:
  type: proxy
  proxy:
    url: https://www.example.com
    rewriteHost: true
```

生产配置中密码由安全文件或受限权限配置提供；root 运行时可使用 root:root 600，专用低权限服务用户则使用 root:服务组 640 或等价授权，并确保父目录可遍历。先读单元中的 User/Group，再设置权限；服务用户必须能读取配置、写入 ACME 存储目录，并有绑定低端口的能力。不要只设 root:root 600 后切换低权限用户导致启动失败。若已有 Web 服务占用 TCP 80/443，按官方文档配置 ACME 或使用已有证书，不能盲目抢占端口。

```sh
sudo systemctl enable --now hysteria-server
sudo systemctl status hysteria-server --no-pager
sudo journalctl -u hysteria-server -n 100 --no-pager
```

防火墙同时允许 UDP Hy2 端口和 TCP 80（证书续期）；不要为了排障关闭整个防火墙。

## 4. 维护

升级前备份配置并执行官方配置校验；重启后确认监听、认证和出口测试。多个端口或 Salamander 混淆属于按证据添加的备用方案，不是默认必需项。
