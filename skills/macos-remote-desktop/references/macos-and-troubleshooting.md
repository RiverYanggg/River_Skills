# Mac 连接与分层排错

## 使用人类在 Mac 上验证过的 SSH 目标

让人类提供 `ssh my-server` 这样的成功连接方式。Mac 的 `~/.ssh/config` 可包含 HostName、Port、User、IdentityFile、IdentitiesOnly、ProxyJump；保留别名就能继承这些设置。不要把服务器的 `hostname -I` 输出当作 Mac 的连接地址，也不要把 SSH 私钥传到服务器。

如果用户只给原始 `ssh -p PORT -i KEY USER@HOST` 命令，可以保留这些选项生成手动隧道命令，或建议其自行建立 SSH 别名。自动助手只接收单个 SSH 目标，不接收整条 shell 命令。

## 标准交付：所有命令在 Mac 本地执行

先从服务器的 `port`/`info` 获取实际端口；以下示例 5902/15902 不是固定值。

```bash
# Mac 本地终端：初始 VNC 密码（与 SSH 密码不同）
ssh my-server '~/.local/bin/mac-desktop password'

# Mac 本地终端：创建隧道；此窗口保持开启
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:15902:127.0.0.1:5902 my-server
```

```bash
# Mac 另一个本地终端：确认实际 VNC 协议已穿过隧道
nc -G 3 -w 3 127.0.0.1 15902
# 预期输出：RFB 003.008（或兼容 RFB 版本）；该测试尚未验证密码

open 'vnc://127.0.0.1:15902'
```

也可 Finder → 前往 → 连接服务器（⌘K），输入同一个 `vnc://...`。使用标准 VNC/密码连接；若界面有认证方式选择，使用 VNC 密码，不使用 Apple 账户/受管理设备身份方式。

macOS 自带的“屏幕共享”客户端与 Mac 系统设置中的“共享服务”不是同一件事。此场景 Mac 是客户端，不需要开启本机被远程控制的服务。

## 可选：一条命令连接

把仓库的 `scripts/mac-connect.sh` 复制到 **Mac** 后：

```bash
# Mac 本地终端
bash mac-connect.sh my-server
# 自定义实例名和本地端口
bash mac-connect.sh my-server research-desktop 15903
```

脚本先通过 SSH 确保该实例服务运行，读取其实际 VNC 端口；检查 Mac 本地端口未被占用，再创建自己的 SSH 隧道、验证 RFB、打开屏幕共享。脚本保持运行，Ctrl+C 只关闭自己的隧道，不停止服务器桌面。它依赖服务器上的 systemd 用户服务；前台部署模式用手工命令。

## 排错顺序

| 现象 | 下一步与判断 |
|---|---|
| Mac 提示 `~/.local/bin/...` 文件不存在 | 这是服务器路径；改用 `ssh my-server '~/.local/bin/mac-desktop ...'`，不要在 Mac 本地直接执行 |
| `ssh -v` 卡在 Connecting/超时 | 还未建立 SSH；核对公网地址、VPN/跳板机、端口，优先使用已成功的 SSH 别名。不要改 VNC |
| Permission denied (publickey) | 检查 Mac SSH 用户/密钥/别名；不需要 VNC 密码，不要求上传私钥 |
| Address already in use | Mac 本地端口冲突；换一个本地端口，同步修改 vnc URL，不杀不明进程 |
| SSH 能登录但转发 administrative prohibited | 服务器 SSH 转发策略可能限制；查 AllowTcpForwarding/PermitOpen/DisableForwarding/授权 key 限制，让管理员按范围开放；不用公网 VNC 绕过 |
| `nc` 无 RFB / connection refused | 检查隧道是否保持、转发目标是否服务器的 127.0.0.1、实际 VNC 端口、是否连错服务器；服务正常但日志无本次连接，先查隧道 |
| RFB 可读但认证失败 | 请求已到 VNC；检查初始密码是否已改、经典 VNC 前 8 字节限制、Mac 密钥串是否缓存旧密码。少量失败后先诊断，避免连续错误触发临时封锁 |
| 连接后黑屏/只有背景/浏览器没出现 | 认证链路已通；查该实例 logs/session.log、xfwm4、dbus 和浏览器日志。不要重启所有用户的桌面 |
| 退出所有 SSH 后连接失败 | 查用户服务和 Linger 状态，不能只说“已设置开机启动” |
| Mac 泛化提示“请开启屏幕共享/远程管理” | 该文字不能定位故障；先用 RFB 测试和服务器日志分层排错，不要求开启 Mac 本机共享 |

Agent 无法访问 Mac 时，只向用户索取最小诊断：实际 SSH 命令/别名、SSH 错误和 `nc` 输出；不索取密码。需要 SSH 调试输出时提醒可遮蔽私有信息，优先最后一段，不要求整份配置或私钥。

## 官方资料

- [Apple：屏幕共享连接](https://support.apple.com/guide/mac-help/share-the-screen-of-another-mac-mh14066/mac)
- [Apple：屏幕共享与 VNC 兼容](https://support.apple.com/en-nz/guide/mac-help/mh11848/mac)
- [OpenSSH：SSH 端口转发与参数](https://man.openbsd.org/ssh)
