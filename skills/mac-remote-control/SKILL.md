---
name: mac-remote-control
description: 让 Linux 服务器上的 Agent（如 Claude Code、Codex）通过 Mac 主动建立的 SSH 反向隧道，读写和操作用户的本地 Mac 文件与命令；适用于"在服务器上改我 Mac 上的项目"或"远程执行 Mac 命令"，不用于 Mac 图形桌面。
---

# 服务器 Agent 管理本地 Mac

**原理：** 由 Mac 发起 `ssh -R 2222:localhost:22 <服务器别名>`，在服务器的 `127.0.0.1:2222` 上打开一个回到 Mac 的入口。服务器侧配置好 `mac-tunnel` 别名后，Agent 即可 `ssh mac-tunnel '命令'` 在 Mac 上执行命令，或把 Mac 目录用 sshfs 挂载到服务器后当作本地目录读写。

这是反向隧道：**服务器不能主动连 Mac，只能走 Mac 建立的隧道**。Mac 休眠、断网或关闭隧道窗口后，所有操作都会失败。

## 执行位置

- **服务器终端：** Agent 的主要工作位置，负责检查隧道、配置别名、执行远程命令、挂载目录。
- **Mac 本地终端：** 只做两件事：启动反向隧道、把服务器公钥加入 `~/.ssh/authorized_keys`（或确认远程登录已开启）。Agent 无法替代用户在 Mac 上输入密码或开启系统设置。

## 从人类获取什么

先利用会话中已有信息，缺少时集中询问：

1. **服务器别名**：Mac 上 `ssh <别名>` 能登录该服务器的别名，用于 Mac 发起反向隧道。
2. **Mac 用户名**（服务器上 `ssh` 登录时使用）。在 Mac 终端执行 `whoami` 获取。
3. **Mac 上项目的绝对路径**（若需要挂载或修改项目）。
4. **隧道端口**，默认 `2222`。同一服务器上多台 Mac 或已有占用时换一个未用端口。
5. Mac 端是否已开启"远程登录"（系统设置 → 通用 → 共享 → 远程登录）。可在 Mac 上执行 `sudo systemsetup -getremotelogin` 确认。

**不索取** Mac 登录密码、sudo 密码或私钥内容。公钥可以直接交给用户粘贴到 Mac 上。

## 流程

1. **检查现状（服务器终端）**
   ```bash
   bash scripts/check-mac-tunnel.sh <ssh-alias> <port>
   ```
   脚本只读，依次检查：隧道端口是否监听、`~/.ssh/config` 是否有别名、免密登录能否执行 `whoami`。全部 PASS 则直接进入第 4 步。

2. **缺少别名或密钥时配置（服务器终端）。** 按 [设置步骤](references/setup.md) 生成专用密钥（不复用其他用途的密钥）、添加 `Host mac-tunnel` 条目。别名名字固定为 `mac-tunnel`，便于其他技能复用。

3. **需要用户在 Mac 上操作时，给出确切命令并等待反馈：**
   - Mac 终端：保持运行 `ssh -R <port>:localhost:22 <服务器别名>`（窗口不能关闭）。
   - Mac 终端：把服务器公钥追加到 `~/.ssh/authorized_keys`。
   - 收到反馈后重新运行第 1 步的检查脚本。

   隧道显示监听但握手被断开（`Connection reset by peer`）时，通常是 Mac 端 sshd 未运行或隧道会话已断开，需要用户在 Mac 上检查，不要反复重试。

4. **执行操作**
   - 运行命令：`ssh mac-tunnel 'cd <路径> && <命令>'`，长命令先说明影响。
   - 读写文件：小改动用 `ssh mac-tunnel` 配合 `cat`/`tee`；需要像本地目录一样用 Read/Edit 工具时，用 sshfs 挂载（见 [设置步骤](references/setup.md) 的挂载部分）。
   - 挂载需要服务器安装 sshfs，若需要 sudo 密码，让用户在服务器终端自行执行 `sudo apt install -y sshfs`。

5. **交付**：报告检查结果、隧道是否依赖 Mac 保持在线、已修改的 Mac 路径和命令摘要。

## 运行约束

- **只通过 `mac-tunnel` 别名访问 Mac**，不把 Mac 的 IP、用户名、私钥路径写入仓库或技能文件。
- **不开启 `GatewayPorts`**，隧道只绑定服务器的 `127.0.0.1`，不暴露到公网。
- **Mac 上的操作以用户身份执行，权限很大。** 对 `rm`、`sudo`、`git push`、覆盖已有文件、修改系统目录的操作，先说明影响并确认；不删除 `~`、系统目录或用户未指定的文件。
- **不在 Mac 上创建管理员账号或修改 sshd 配置**，除非用户明确要求。
- 在 Mac 上创建临时文件时放在用户指定目录或独立子目录（如 `~/claude_test/`），用完清理。

## 验证与诚实交付

交付时分开说明：

- 服务器侧检查脚本的输出（隧道、别名、免密命令执行）。
- 实际完成的 Mac 操作（例如创建或运行了哪个文件）。
- 尚未验证的部分（例如 sshfs 挂载、真实项目的编辑）。

隧道依赖 Mac 端保持在线，每次新会话都应先运行检查脚本，不假定上次的连接仍然有效。

## 工具入口

```bash
# 服务器终端；路径相对于本技能目录
bash scripts/check-mac-tunnel.sh              # 默认别名 mac-tunnel，端口 2222
bash scripts/check-mac-tunnel.sh mac-tunnel 2222
```

完整设置、sshfs 挂载、常见错误排查见 [references/setup.md](references/setup.md)。
