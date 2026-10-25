# 服务器安装与运行

本页所有未特别标注的命令均在 **Linux 服务器、目标普通用户的终端**执行。不要在 Mac 本机安装 Linux 软件包，不使用 root 作为桌面所属用户。

## 1. 检查环境

Agent 自行读取机器信息：

```bash
uname -srm
id
cat /etc/os-release
command -v Xtigervnc Xvnc tigervncpasswd vncpasswd xfce4-session dbus-run-session xauth xdpyinfo
command -v google-chrome google-chrome-stable chromium firefox
ss -ltn
ls -la /tmp/.X11-unix
systemctl --user is-system-running
```

`degraded` 不一定阻止此桌面运行，检查具体失败单元。若 Agent 沙箱看不到主机进程或不能操作 D-Bus，按其权限机制访问主机；不要误判依赖缺失。无 systemd 的容器使用前台会话，不能承诺用户服务或开机启动。

## 2. 安装缺失依赖

优先使用已安装版本。Ubuntu/Debian 上，实际需要管理员安装时，参考：

```bash
# 服务器终端；需要管理员权限。只在确实缺少依赖时执行
sudo apt-get update
sudo apt-get install --no-install-recommends \
  tigervnc-standalone-server tigervnc-common tigervnc-tools \
  xfce4 xfce4-terminal dbus-x11 xauth x11-utils x11-xserver-utils iproute2 \
  fonts-dejavu-core fonts-noto-cjk
```

不要仅为了 VNC 安装/更改 display manager，不需要重启服务器。浏览器安装按用户选择和发行版官方来源处理：Ubuntu 某些浏览器包可能是 Snap，不能把 Debian 的包名直接套用；`configure` 不下载浏览器。已有 Chrome/原生 Firefox 可直接复用，Snap 的 profile 访问受限时应先确认可用路径或选择原生浏览器。

**无 sudo、已有 XFCE 和运行库时**：在技能目录运行：

```bash
# 服务器终端；只下载并解包已配置 apt 软件源中的 TigerVNC 包
bash scripts/prepare-debian-runtime.sh
```

它检查同机共享库，不修改系统包数据库；不解决缺失桌面或库依赖。apt 仓库不可达、发行版不匹配、缺库时明确报告具体阻塞，不下载来源不明的二进制，不使用另一台机器的动态库包强行覆盖。

Fedora/RHEL/Arch 等使用官方发行版依赖和 TigerVNC 文档进行适配；不要运行本页的 apt 命令。统一的桌面控制脚本仍要求找到 XFCE、Xvnc、vncpasswd、xauth、xdpyinfo、dbus-run-session 和 ss。

## 3. 创建用户实例

在技能目录运行。`my-server` 是用户在 **Mac 上**已经能使用的真实 SSH 别名；服务器无需解析该别名。

```bash
# 服务器终端
python3 scripts/desktop.py configure --ssh-target my-server --dry-run
python3 scripts/desktop.py configure --ssh-target my-server
~/.local/bin/mac-desktop start
~/.local/bin/mac-desktop status
~/.local/bin/mac-desktop verify
```

脚本自动选择空闲显示号 :2..:99，端口为 5900+显示号；不要假定总是 5902。默认命令名为 `mac-desktop`。多实例使用 `--name`（在子命令之前）：

```bash
python3 scripts/desktop.py --name research-desktop configure \
  --ssh-target my-server --geometry 1920x1200 --browser /usr/bin/google-chrome
~/.local/bin/research-desktop start
```

其他选项：`--xvnc /path/to/Xtigervnc`、`--vncpasswd /path/to/tigervncpasswd`、`--url https://example.com`、`--proxy http://127.0.0.1:PORT`。只有用户需要且该代理在服务器可达时才使用 `--proxy`；不接受含凭据的 URL。Firefox 代理通过其独立 profile 人工配置。`--no-browser` 仅在用户不需要自动打开浏览器时使用。

`configure` 不启用 lingering、不安装系统包、不自动启动桌面；重复运行保留已有密码和显示号。改变已有配置前先保存应用并 `stop`，否则脚本拒绝更改活动实例。配置更新后再 `start`；若只更新脚本也应在保存工作后重启以启用新代码。

默认实例文件：

| 位置 | 内容 |
|---|---|
| `~/.local/share/macos-remote-desktop/mac-desktop/` | 私有实例目录（700），包括配置、凭据、日志和 browser profile |
| `~/.config/systemd/user/mac-desktop.service` | 用户服务 |
| `~/.local/bin/mac-desktop` | 控制命令，可在技能仓库移动后继续使用 |

设置 XDG_DATA_HOME/XDG_CONFIG_HOME 时会使用对应用户目录。控制脚本保存实际实例/服务路径，在隔离桌面内部运行也能找到原始用户服务。

## 4. 验证，不只看端口

```bash
~/.local/bin/mac-desktop port
~/.local/bin/mac-desktop info
~/.local/bin/mac-desktop verify
# 可选；输出路径不得已存在；截图留在服务器本地
~/.local/bin/mac-desktop verify --screenshot /tmp/my-desktop-check.png
```

`verify` 检查 ss 回环监听、RFB、密码认证和实际 framebuffer。仅依赖 Python 标准库及服务器通常已有的 libgcrypt；缺少时显示验证失败，不静默降低标准。之后检查 `logs/session.log`，确认 xfwm4/xfce4-panel/浏览器属于本人实例。需要时查看截图，不能因 VNC 图像可读就断言浏览器已启动。

从服务器不能验证 Mac 本地端口、Mac SSH 配置或苹果客户端实际登录。交付给用户后由其做本地连通性验证。

## 5. 密码与日常管理

```bash
# 服务器终端；只有这个命令会显示初始密码，勿让 Agent 转录进公开材料
~/.local/bin/mac-desktop password

# 服务器交互终端；新密码前 8 个 ASCII 字符有效，拒绝/不设置 view-only 密码即可
~/.local/bin/mac-desktop change-password

~/.local/bin/mac-desktop stop
~/.local/bin/mac-desktop start
~/.local/bin/mac-desktop restart
```

改密码不需要关闭桌面，下一次连接生效；初始明文密码文件随之删除。Agent 不需要人类在聊天中发送新密码。

## 6. 后台持久性

默认服务在用户管理器运行时可用；enabled 不代表跨全部登出或开机无需登录就能运行。

```bash
loginctl show-user "$(id -un)" -p Linger
```

只有用户需要这项行为时才按实际权限执行 `loginctl enable-linger USER`；必要时管理员运行。记录先前状态，不把它作为所有部署的强制步骤。默认保留 SSH 隧道期间可以使用桌面；关闭所有登录后桌面可能停止。

没有可用的用户管理器时，可先在前台运行并验证（保持服务器终端）：

```bash
~/.local/bin/mac-desktop session
```

这种情况下不要交付会调用 `systemctl --user start` 的 Mac 自动助手，改用手工隧道步骤。若需持久运行，按用户授权选其已有进程管理器或管理员配置，说明与 systemd 用户服务的差别。

## 7. 卸载

先保存应用，停止并禁用**本实例**的用户服务。删除前以 `info` 确认实际路径并列出给用户审阅；只移除本技能创建的服务、控制命令与私有实例目录，不卸载共享的 XFCE/浏览器或重启其他桌面。浏览器 profile 有个人数据，应按用户意图保留或备份。不要自动 disable-linger：它可能被同一账号的其他服务依赖。

## 官方资料

- [TigerVNC Xvnc：监听、认证、密码文件参数](https://tigervnc.org/doc/Xvnc.html)
- [TigerVNC vncpasswd：8 字符限制、密码文件与 filter 模式](https://tigervnc.org/doc/vncpasswd.html)
- [systemd loginctl：用户 lingering](https://www.freedesktop.org/software/systemd/man/latest/loginctl.html)
