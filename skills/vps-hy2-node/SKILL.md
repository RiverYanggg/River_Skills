---
name: vps-hy2-node
description: 在用户自有 Linux VPS 上按 Hysteria 2 官方文档部署个人节点，生成 Mihomo/Clash Meta 与 Karing 可用的 YAML，并指导 macOS、Android 导入和验证；适用于用户已提供 VPS SSH 访问且明确要自建代理节点的场景。
---

# VPS Hysteria 2 自建节点

完成从 VPS 环境检查、TLS 证书、Hysteria 2 服务、认证、开机自启，到客户端 YAML 生成和实际出口验证的完整流程。默认只服务个人使用，保留现有 SSH 和其他服务。

## 开始前获取的信息

向用户确认或复用会话中的：

- VPS 地址、SSH 端口、登录用户和登录方式；密码只在交互式认证中使用，不写入文件、日志或回答。
- 本地系统（macOS/Windows）和客户端（Clash Verge Rev、FlClash、Karing 等）。
- 是否已有网站域名；没有时可使用指向 VPS 的 `sslip.io` 主机名作为证书名称，前提是 ACME 能从公网访问 TCP 80。

不要把真实 IP、密码、UUID、节点密码、私钥、订阅链接提交到 Git 或输出到公开文档。

## 工作流

1. 通过 SSH 探测发行版、架构、内存、磁盘、已有监听端口和 systemd 服务；备份将修改的配置。2 GB RAM 足够运行个人 Hy2，安装浏览器/桌面会增加资源占用，不是节点必需项。
2. 按 [部署参考](references/deployment.md) 安装官方 Hysteria 2，使用独立认证密码和有效 CA 证书。保留 SSH、TCP 80（ACME）和既有服务；端口冲突先探测再选择。
3. 配置服务为 systemd 开机自启，使用最小权限用户运行；先用官方配置检查，再查看 `systemctl status` 和日志。
4. 生成完整客户端 YAML：服务器地址、端口、密码、SNI/证书验证必须与实机一致。对 Mihomo/Clash Meta 使用 `type: hysteria2`；Karing 使用其当前版本支持的 Hy2 字段，并在说明中标出需要在 App 内单独设置的项目。
5. 将配置保存到用户指定的本地任务目录，权限设为仅当前用户可读。通过本地客户端实际请求 `api.ipify.org` 或 `ipinfo.io/json`，核对出口 IP；不要只以延迟接口或服务 active 作为成功证据。
6. 交付导入说明、节点选择、TUN/DNS/Fake-IP 影响、日志和维护命令。记录测试所用网络类型，区分服务器问题与运营商线路问题。

## 运营商结论记录

本案例的实测结论是：**移动不行，电信和联通可以**。把它记录为该 VPS/IP 与运营商线路的实测结果，不要推广成所有 VPS 或所有移动用户的普遍规律；遇到移动不可用时，先用其他运营商或中转线路验证，避免无证据地反复改端口和协议。

## 参考资料

- 部署细节和安全边界：[references/deployment.md](references/deployment.md)
- 客户端 YAML 与导入流程：[references/clients.md](references/clients.md)
- 验证、日志和维护：[references/verification.md](references/verification.md)
