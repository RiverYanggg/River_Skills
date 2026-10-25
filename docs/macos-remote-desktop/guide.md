# macOS Remote Desktop Skill

给 Agent 使用的技能：在 Linux 服务器建立独立 XFCE/TigerVNC 桌面，供 Mac 通过 SSH 隧道和系统自带“屏幕共享”连接。适合远程浏览器、个人桌面，以及没有物理显示器的服务器。

## 技能装在哪里？

**推荐装在目标 Linux 服务器上，让服务器上的 Agent 配置服务器。** 你的 Mac 不需要安装 Windows App，不需要开启本机“共享”，也不需要安装本技能才能连接。

如果 Agent 在 Mac 上运行，也可使用本技能，通过你已有的 SSH 别名在服务器执行部署。服务器上的路径与 Mac 上的路径不同；所有操作说明都会区分执行位置。

## 安装给 Agent

将本仓库克隆到服务器的任意工作目录，再将整个 `skills/macos-remote-desktop` 目录复制到 Agent 的技能目录。例如 Codex 的默认个人技能目录：

```bash
# Linux 服务器终端；先进入已经克隆的仓库根目录
mkdir -p ~/.codex/skills
cp -R skills/macos-remote-desktop ~/.codex/skills/
```

如果设置了自定义技能目录，使用对应目录。已有同名技能时先比较或备份，避免直接覆盖。其他支持 SKILL.md 的 Agent 按其技能加载方式安装；不保证所有 Agent 自动发现的目录相同。新会话中调用更容易确保已加载。

GitHub 发布时保留目录结构，不提交任何运行时目录或密码文件。本仓库无需携带 TigerVNC 二进制。

## 给 Agent 的完整提示词

复制下面内容，替换 SSH 别名及实际需求：

> 使用 $macos-remote-desktop 为当前 Linux 服务器配置我自己的独立图形桌面。
> 我本地是 macOS，希望用系统自带“屏幕共享”，不安装 Windows App。
> 我在 Mac 上已经可以通过 `ssh my-server` 登录，连接说明请复用 `my-server`，不要使用服务器自行探测到的内网地址。
> 桌面属于当前普通用户。默认分辨率 1600×1000，浏览器优先复用已有安装。
> 不影响其他用户的图形界面。请完成服务器侧验证，并把 Mac 本地连接命令、密码查询、启动停止、改密码及持久性说明交付给我。

如有需要，可补充：

```text
指定 Linux 用户：当前用户 / 指定用户名
浏览器：自动选择 / Chrome / Firefox / 已有可执行文件路径
浏览器代理：不需要 / 服务器上可访问的代理地址（不要发送代理密码）
分辨率：1600x1000 / 自定义
退出所有 SSH 后继续运行及开机启动：需要 / 不需要
没有 sudo 权限：是 / 否 / 不知道
```

Agent 应自己探测发行版、依赖、空闲显示号和端口，不能要求人类先收集这些机器可读信息。人类无需提供 SSH 私钥内容或在聊天中发送密码。

## 你以后如何连接

Agent 配置完成后会交付实例对应的实际命令。以下是默认实例和示例端口，**以部署结果为准**：

```bash
# Mac 本地终端：查看 VNC 初始密码
ssh my-server '~/.local/bin/mac-desktop password'

# Mac 本地终端：建立隧道，保持窗口开启
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:15902:127.0.0.1:5902 my-server
```

```bash
# Mac 另一个本地终端：测试和打开桌面
nc -G 3 -w 3 127.0.0.1 15902
# 正常会看到 RFB 003.008
open 'vnc://127.0.0.1:15902'
```

也可以将 `skills/macos-remote-desktop/scripts/mac-connect.sh` 复制到 Mac，在本地运行：

```bash
# Mac 本地终端；脚本读取服务器实际端口、建立隧道、验证协议再打开桌面
bash mac-connect.sh my-server
```

连接助手在前台保持运行，Ctrl+C 只关闭它自己创建的隧道。它复用 `~/.ssh/config`，支持通过该文件配置的端口、密钥和跳板机。

## 支持范围与验证范围

- 默认实现：Linux、普通用户、XFCE/X11、TigerVNC、systemd 用户服务；不接管现有 xrdp 会话。
- 自动化工具复用已安装依赖；Debian/Ubuntu 的 TigerVNC 用户目录安装有配套步骤。缺失桌面/系统库时需要管理员安装。
- Fedora/RHEL/Arch 等由 Agent 根据发行版适配依赖；没有把它们标记为已实机测试。
- 不提供音频、GPU 加速或文件拖放保证；这是一条基本的桌面/浏览器连接路径。
- 服务器认证与图像传输可自动验证；Mac 实际连接仍由用户在 Mac 完成。
- 不需要开放公网 VNC 端口。Mac 需要能通过用户提供的 SSH 方式连接目标服务器。

## 仓库内容

| 路径 | 用途 |
|---|---|
| `skills/macos-remote-desktop/SKILL.md` | Agent 入口与决策约束 |
| `skills/macos-remote-desktop/references/` | 服务器部署、Mac 连接与排错 |
| `skills/macos-remote-desktop/scripts/desktop.py` | 生成独立实例、用户服务、控制命令 |
| `skills/macos-remote-desktop/scripts/verify_vnc.py` | VNC 认证与画面验证，可选本地截图 |
| `skills/macos-remote-desktop/scripts/mac-connect.sh` | Mac 连接助手 |
| `tests/` | 不改已有桌面的检查及可选 VNC 集成测试 |

## 运行检查

```bash
# Linux 服务器的仓库根目录；单元测试不需要 root、网络或修改已有桌面
python3 -m unittest discover -s tests -v
bash -n skills/macos-remote-desktop/scripts/mac-connect.sh

# 可选：启动临时回环 VNC 进程，验证认证与截图；退出时清理
python3 tests/macos_remote_desktop/integration_vnc.py --xvnc /path/to/Xtigervnc --vncpasswd /path/to/tigervncpasswd

# 可选：完整 XFCE/Chrome 临时部署（需要 systemd 用户管理器和图形依赖）
python3 tests/macos_remote_desktop/integration_desktop.py --xvnc /path/to/Xtigervnc \
  --vncpasswd /path/to/tigervncpasswd --browser /path/to/google-chrome
```

实现和测试细节见 [验证记录](validation.md)。
