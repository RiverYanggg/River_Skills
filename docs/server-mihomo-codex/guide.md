# 服务器 Mihomo + Codex 使用指南

此技能面向无图形界面的 Linux 服务器，可由本机 Agent 或通过 SSH 的本地 Agent 执行。默认普通用户安装，不需要将私人订阅上传到 GitHub。

## 安装技能

```bash
# 在要调用 Agent 的机器上执行；目标目录已存在时先比较/备份
cd River_Skills
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/server-mihomo-codex "${CODEX_HOME:-$HOME/.codex}/skills/"
```

在新会话中：

> 使用 $server-mihomo-codex，连接 `my-server`，为当前普通用户安装 Mihomo、导入我提供的订阅，选择可用美国节点，配置后台服务和每次 Bash 登录时的出口检查，再安装 Codex。我使用 ChatGPT 订阅，网页登录由我自己完成。请保留已有配置并完成网络验证。

提供可用的 SSH 连接方式和私密订阅；无需提供私钥内容、ChatGPT 密码。端口、架构、发行版由 Agent 检测。

## 完整部署流程

唯一部署说明位于技能内部的 [setup.md](../../skills/server-mihomo-codex/references/setup.md)，复制技能后仍可独立阅读。按顺序覆盖：

1. 检查系统、软件、端口、用户服务和 SSH 目标。
2. 官方下载安装，网络受限时由本机下载/校验/上传。
3. 私密导入订阅，保留 DNS、节点组和规则，验证配置。
4. 配置仅回环监听的用户后台服务。
5. 选择节点并同时检查 OpenAI 专用组。
6. 配置代理变量、手动 `proxycheck` 和交互式登录自动检查。
7. 安装 Codex，验证代理出口、OpenAI 登录接口、账户登录状态。

诊断和完成标准见 [verification.md](../../skills/server-mihomo-codex/references/verification.md)。

## 日常使用

以下在服务器终端执行；安装后实际路径以部署交付为准：

```bash
source ~/.bashrc
proxycheck
systemctl --user status mihomo.service
systemctl --user restart mihomo.service
journalctl --user -u mihomo.service -n 50 --no-pager
codex login --device-auth
codex login status
codex
```

正常登录提示示例：`代理已开启，出口: US ✓`。出口检查只检查连通性和国家，不代替 Codex 身份验证。没有期望地区时接受任何有效两字母国家码；要检查美国则设 `MIHOMO_EXPECTED_COUNTRY=US`。

## 文件与恢复

- 内核：`~/.local/opt/mihomo/<version>/`，入口 `~/.local/bin/mihomo`。
- 订阅配置和 Shell 辅助文件：`~/.config/mihomo/`，目录 700、含凭据文件 600。
- 服务：`~/.config/systemd/user/mihomo.service`。
- Shell：仅在现有 `.bashrc` 中补充缺失 source 行；先保存备份。
- Codex：原生版本目录和 `~/.local/bin/codex`，实际目标路径按安装包探测。

停用代理时，停止/禁用本人服务，移除 `.bashrc` 中这次添加的 source 行并清除当前 Shell 的大小写代理变量；保留订阅备份，避免误删其他工具的配置。回滚到此前配置时用备份恢复并重启本人服务。不要直接删除整个 `.config` 或 `.local`。

用户服务 enable 不自动保证无人登录时开机运行；linger 或系统服务按实际持久性需求和权限另行配置。共享超算多登录节点需逐主机验证，本地回环代理不跨主机共享。

## 依赖和限制

运行使用 Bash、curl、Linux Mihomo、systemd 用户管理器（无管理器时可前台运行）；订阅转换按需要使用 YAML 解析器。无需图形桌面，原生 Codex 不要求 Node/npm。账号登录需要用户可用的 ChatGPT 权益与授权；本文不保证特定套餐、地区或节点永久可用。

实测范围和脚本模拟测试详见 [验证记录](validation.md)。
