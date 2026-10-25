---
name: macos-remote-desktop
description: 为 Linux 服务器部署、验证或修复独立的 XFCE/TigerVNC 图形桌面，让 macOS 用户通过 SSH 隧道使用自带屏幕共享连接；适用于远程浏览器和个人桌面，不接管其他用户的现有桌面。
---

# macOS 连接 Linux 个人桌面

默认方案：**个人 XFCE/X11 会话 → 仅回环监听的 TigerVNC → SSH 隧道 → Mac 自带屏幕共享**。
不需要 Windows App，不依赖物理显示器，也不要求修改 Mac 的“共享”设置。

## 执行位置

- **推荐：在目标 Linux 服务器上安装并调用本技能。** Agent 在目标普通用户身份下安装依赖、生成桌面和用户服务、完成服务器验证。Mac 只负责 SSH 和查看桌面。
- 若 Agent 在 Mac 上：先确认用户指定的 SSH 目标，通过 SSH 在服务器执行部署；仓库不必安装到 Mac 的 Agent 技能目录。Mac 上的连接助手可独立使用。
- 不把服务器命令直接交给用户在 Mac 本机执行。交付时每个命令块明确写“服务器终端”或“Mac 本地终端”。

## 从人类获取什么

先利用当前会话已有信息，不重复索取。真正缺少时，集中询问：

1. **Mac 已经能成功使用的 SSH 别名或完整连接方式**，例如 `ssh work-server`。别名优先；可保留本地 SSH 配置中的端口、私钥、ProxyJump。服务器本机看到的内网 IP 不代表 Mac 可达。
2. **桌面所属 Linux 用户**，默认当前登录的普通用户。使用另一账号前验证权限和用户意图。
3. 可选需求：浏览器选择、分辨率、是否需要特定代理、是否需要退出全部 SSH/重启后仍运行。未指定时：1600×1000，复用可用浏览器，不设置新代理，不启用 lingering。

管理员安装确实需要权限时，让人类在可信终端输入 sudo 密码，或按当前工具的权限流程申请；**不索取私钥内容、sudo 密码、网站密码**。SSH 私钥留在 Mac，SSH 登录凭据与 VNC 密码分开。
SSH 别名未知时仍可先完成服务器侧工作，但不能编造一个“可用的 Mac 连接地址”。

## 部署流程

1. **确认在哪台机器及以谁的身份执行。** 检查 `uname`、`id`、发行版、HOME、systemd 用户总线、已有显示号/监听端口/桌面/浏览器、sudo 和包管理器。不要把 Agent 的进程沙箱当成主机完整状态；套接字、D-Bus 或 sudo 因沙箱失败时走环境规定的权限流程。
2. 读 [服务器安装与运行](references/server-setup.md)。先复用依赖；缺少时按实际发行版安装。Debian/Ubuntu 提供仅下载并解包 TigerVNC 的用户目录回退方案；它**不能凭空补齐缺失的 XFCE 或系统库**。其他发行版按其官方包管理流程适配，不声称已自动支持。
3. 以目标普通用户运行 `scripts/desktop.py configure`。它自动选空闲显示号/端口，隔离 XFCE 设置与浏览器 profile，保存配置、密码和控制命令，安装 systemd **用户**服务。使用 `--dry-run` 先查看具体计划；已有配置重跑保留端口与密码。非本技能管理的同名文件不覆盖。
4. 用生成的控制命令 `start` 启动；用 `status`、`verify` 验证。没有可用的 systemd 用户管理器时，使用该脚本的 `session` 前台模式，注明终端断开后的实际限制；不要擅自转为 root 桌面或修改系统级启动服务。
5. 验证成功后，按 [Mac 连接与排错](references/macos-and-troubleshooting.md) 输出**基于真实 SSH 目标**的本地连接步骤，或交付 `scripts/mac-connect.sh`。用户可在自己的 Mac 复制执行，无需安装第三方远程桌面客户端。

## 运行约束

- 新建目标账号自己的桌面，不重启 xrdp，不使用其他账号的 Xauthority、VNC 密码、浏览器 profile，不杀其他用户会话。已存在的本人实例优先诊断/复用。
- VNC 仅监听 `127.0.0.1`，X11 禁止 TCP。默认 `VncAuth` 兼容 Mac 自带客户端，传输由 SSH 保护；不开放公网 590x、不关防火墙、不使用 `SecurityTypes=None`。
- 经典 VNC 密码只有前 8 字节有效。默认生成 8 位随机 ASCII 密码，文件权限 600、实例目录 700；明文初始密码不进入仓库/日志/聊天。交付查询命令，允许用户在自己的终端查看或修改。
- 浏览器独立 profile；保留浏览器沙箱。不加 `--no-sandbox`、不固定调试端口、不改全局语言/时区、不加入规避指纹的设置。
- 代理仅按用户需要配置为该浏览器的参数，核实它在**服务器**上可达；不把 Mac 的 localhost 代理直接写进服务器，不复制这次会话的私有端口。含凭据的代理 URL 不写入命令行/配置，改为人工在浏览器配置或使用已有安全凭据方案。
- `loginctl enable-linger` 会改变账号后台运行策略：只有用户需要跨登出/重启保持服务时才执行，遵守实际权限。仅创建 enabled 的用户服务不等于开机无登录即可运行。
- 停止/重启桌面会关闭应用。排错优先观察；涉及已有未保存工作时先说明影响，沿用已有授权，不添加固定的重复审批步骤。

## 必须验证与诚实交付

服务器侧记录以下证据：

- 用户服务/前台进程正常、XFCE 窗口管理器启动；浏览器实际打开或明确说明缺失。
- `ss` 显示 VNC 仅回环监听，不能只检查“有端口”。
- `verify` 读取 RFB 协议、完成 VNC challenge-response、接收真实 framebuffer；可按需保存截图供本地查看。验证依赖 libgcrypt，缺失时明确报告哪个阶段未验证。
- 重复 configure 不重置密码、不新增第二个实例；密码文件和配置权限正确。

**服务器验证 ≠ Mac 实际连接成功。** 交付中分别说明已验证部分，以及仍需人类在 Mac 验证的 SSH/VNC 链路。失败按“Mac → SSH → 转发 → VNC 认证 → 图形桌面”分层定位，先读日志，不凭 Mac 的通用报错认定服务器未开启共享。

最终交付至少包含：实例名/所属用户、回环端口、浏览器与代理选择、密码查询方式、Mac 的 SSH 隧道与 `open vnc://...` 命令、启动/停止/改密码命令、持久性限制。不得把用户私有主机/IP/密钥路径或运行生成的密码文件复制进可发布的技能仓库。

## 工具入口

```bash
# 服务器终端；路径相对于本技能目录
python3 scripts/desktop.py --help
python3 scripts/desktop.py configure --help

# 示例目标是占位 SSH 别名，必须替换为用户真实别名
python3 scripts/desktop.py configure --ssh-target my-server --dry-run
python3 scripts/desktop.py configure --ssh-target my-server
~/.local/bin/mac-desktop start
~/.local/bin/mac-desktop verify
```

脚本只准备和管理当前账号的实例；系统依赖安装、SSH 目标可达性和 Mac 操作仍按环境执行，不能用“脚本成功”替代完整交付。
