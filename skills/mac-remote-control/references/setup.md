# 设置步骤：服务器 Agent 管理 Mac

以下所有占位符都需要替换为用户的真实值，不要照抄示例：

- `<server-alias>`：Mac 上 `ssh <server-alias>` 能登录服务器的别名
- `<mac-user>`：Mac 上的用户名（Mac 终端执行 `whoami`）
- `<mac-project-path>`：Mac 上项目目录的绝对路径（例如 `/Users/<mac-user>/my-project`）
- `<port>`：隧道端口，默认 `2222`

## 1. Mac 端：开启远程登录

**Mac 本地终端**

```bash
sudo systemsetup -getremotelogin     # 应显示 On
```

若显示 Off：系统设置 → 通用 → 共享 → 远程登录 → 开启。

## 2. 服务器端：生成专用密钥

**服务器终端**

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_mac -N "" -C "server-to-mac"
cat ~/.ssh/id_ed25519_mac.pub        # 把这一行交给用户，下一步用
```

## 3. Mac 端：授权服务器公钥

**Mac 本地终端**（把第 2 步输出的公钥整行替换下面的 `<PUBLIC_KEY_LINE>`）

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo '<PUBLIC_KEY_LINE>' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

## 4. 服务器端：添加 SSH 别名

**服务器终端**，把下面的 `<mac-user>` 替换成 Mac 用户名：

```bash
cat >> ~/.ssh/config <<'EOF'

# Mac 反向隧道：需要 Mac 上已执行 ssh -R <port>:localhost:22 <server-alias>
Host mac-tunnel
    HostName localhost
    Port 2222
    User <mac-user>
    IdentityFile ~/.ssh/id_ed25519_mac
    IdentitiesOnly yes
    StrictHostKeyChecking accept-new
EOF
chmod 600 ~/.ssh/config
```

若 `Port` 不是 2222，同时修改 `Port` 与 Mac 端 `-R` 的端口。

## 5. Mac 端：建立反向隧道

**Mac 本地终端**（保持该窗口打开，关闭即断开）

```bash
ssh -R 2222:localhost:22 <server-alias>
```

需要自动重连时可以加 `-o ServerAliveInterval=30 -o ExitOnForwardFailure=yes`，但仍需 Mac 保持在线。

## 6. 服务器端：验证

**服务器终端**

```bash
bash scripts/check-mac-tunnel.sh        # 在本技能目录下运行
ssh mac-tunnel 'whoami; echo $HOME'    # 应返回 Mac 用户名和家目录
```

## 7. 可选：sshfs 挂载 Mac 目录

sshfs 让 Agent 可以把 Mac 目录当本地目录使用（Read/Edit 工具直接生效）。

**服务器终端**（需要 sudo 时由用户自己输入密码）

```bash
sudo apt install -y sshfs            # Debian/Ubuntu；其他发行版用对应包管理器
mkdir -p ~/local_proj
sshfs mac-tunnel:<mac-project-path> ~/local_proj
ls ~/local_proj                      # 能看到 Mac 上的文件即成功
```

卸载：

```bash
fusermount -u ~/local_proj
```

注意：

- 隧道断开后挂载会失效，需要重新执行 `sshfs`。
- 大量小文件（如 `node_modules`）会很慢，尽量只挂载源码目录。
- 挂载点不要放在仓库内，避免被 git 误提交。

## 8. 常见错误

| 现象 | 可能原因 | 处理 |
|---|---|---|
| `Connection refused` | Mac 端 sshd 未开启，或隧道未建立 | Mac 上检查远程登录；重新执行第 5 步 |
| `Connection reset by peer`（TCP 能连） | 隧道会话已断开，或 Mac 端 sshd 异常 | Mac 上检查 `lsof -iTCP:22 -sTCP:LISTEN`；重启隧道窗口 |
| `Permission denied (publickey)` | 公钥未加入 `authorized_keys`，或用户名错误 | 核对第 3、4 步 |
| `Permission denied`（密码） | 免密未生效，BatchMode 下直接失败 | 按第 2、3 步重新授权 |
| `Could not resolve hostname mac-tunnel` | 未添加 `Host mac-tunnel` | 执行第 4 步 |
| 端口已被占用 | 其他隧道或服务占用了 `<port>` | 换端口，同时改 Mac 的 `-R` 与服务器的 `Port` |

## 9. 安全边界

- 隧道只绑定服务器回环地址；不要为此开启 `GatewayPorts`，不要修改服务器防火墙把 `<port>` 暴露到公网。
- 专用密钥只用于此用途，不要复用 GitHub、集群等其他用途的密钥。
- 不把 Mac 用户名、服务器地址、密钥路径写入公开仓库。
- Mac 端 `authorized_keys` 中只保留确需授权的公钥，不再使用时删除对应行。
