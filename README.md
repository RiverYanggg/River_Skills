# River_Skills

RiverYanggg 的可复用 Agent 技能库。每个技能说明用途、执行位置、所需输入、安装方式、验证范围和操作边界，让新服务器上的 Agent 可以直接接手。

## 技能目录

| 技能 | 用途 | 主要执行位置 | 人类需要提供 | 使用文档 |
|---|---|---|---|---|
| [macos-remote-desktop](skills/macos-remote-desktop/SKILL.md) | 为 Linux 建立独立 XFCE/TigerVNC 桌面，Mac 使用自带“屏幕共享”连接 | Linux 服务器；Mac 负责 SSH 隧道和查看桌面 | Mac 已能使用的 SSH 别名；目标用户默认当前用户；可选浏览器、代理、分辨率及持久运行需求 | [完整指南](docs/macos-remote-desktop/guide.md) · [验证记录](docs/macos-remote-desktop/validation.md) |
| [server-mihomo-codex](skills/server-mihomo-codex/SKILL.md) | 配置 Linux Mihomo 订阅代理、后台服务、登录出口检测与 Codex 订阅登录链路 | Linux 服务器；可由本地 Agent 经 SSH 执行 | 可用 SSH 连接、私密订阅/配置；可选出口国家和登录方式 | [完整指南](docs/server-mihomo-codex/guide.md) · [验证记录](docs/server-mihomo-codex/validation.md) |

新增、重命名或删除技能时，同时维护本表和下方对应说明。Agent 的仓库维护规则见 [AGENTS.md](AGENTS.md)。

## 安装与调用

先将仓库克隆到需要使用技能的机器，再按技能说明选择执行位置。以下以 Codex 为例；其他支持 `SKILL.md` 的 Agent 使用其对应的技能目录。

```bash
# 在需要安装技能的机器上运行；macos-remote-desktop 推荐在 Linux 服务器安装
git clone https://github.com/RiverYanggg/River_Skills.git
cd River_Skills

# 安装单个技能；若目标已存在，先比较或备份，不直接覆盖
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/macos-remote-desktop "${CODEX_HOME:-$HOME/.codex}/skills/"
```

复制的是整个技能目录，不只是 `SKILL.md`。新会话中调用 `$macos-remote-desktop`。更新仓库后，已安装的副本不会自动同步；比较变化并更新所需技能。

运行时配置、密码、浏览器资料和服务文件保存在目标机器的用户目录，**不保存在本仓库中**。GitHub 仓库地址、技能安装位置和实际桌面实例是不同概念。

## macos-remote-desktop

**用途：** 为 Linux 服务器上的普通用户配置个人图形桌面和浏览器。连接链路为 XFCE/X11 → 仅回环监听的 TigerVNC → SSH 隧道 → Mac 自带“屏幕共享”，无需 Windows App 或物理显示器。

**在哪里使用：** 推荐让服务器上的 Agent 调用技能。若 Agent 在 Mac 上，也可以通过用户指定的 SSH 方式在服务器部署；Mac 的连接助手可独立使用。说明和命令明确区分“服务器终端”与“Mac 本地终端”。

**人类需要提供：**

- Mac 已验证可用的 SSH 别名，例如 `my-server`，或完整连接方式。不要把服务器检测到的内网地址直接当作 Mac 的连接地址。
- 桌面所属 Linux 账号，默认当前普通用户。
- 可选：浏览器、分辨率、服务器可达的代理，以及退出全部 SSH/重启后是否仍需保持服务。

无需提供 SSH 私钥内容、sudo 密码或网站密码。机器的发行版、依赖和空闲端口由 Agent 自行检测。

**调用示例：**

> 使用 $macos-remote-desktop 为当前 Linux 服务器配置我的独立图形桌面。
> 我本地是 macOS，已经可以通过 `ssh my-server` 登录，请复用这个别名。
> 桌面属于当前普通用户，分辨率使用默认值，浏览器优先复用已有安装。
> 请完成服务器侧验证，交付 Mac 本地连接、密码查询和日常管理命令。

**部署结果：** 独立的桌面实例、systemd 用户服务/可选前台会话、浏览器 profile、密码管理命令、Mac 连接助手与排错说明。默认分辨率 1600×1000；自动选择空闲显示号和端口，重复配置保留密码。不接管其他用户的现有桌面。

**依赖与限制：** 默认针对 Linux、XFCE、TigerVNC 和 systemd 用户管理器；Debian/Ubuntu 提供用户目录安装 TigerVNC 的回退流程。缺少桌面/系统库时仍需管理员协助。服务器端验证不等于真实 Mac 链路已验证；其他发行版、音频/GPU/文件拖放等不在已实测承诺内。

**验证：** 已通过 17 项自动检查，以及临时 VNC、完整 XFCE/Chrome 部署的实机集成测试；真实 Mac 连接仍需首次使用时确认。详见[验证范围与限制](docs/macos-remote-desktop/validation.md)。

完整安装、连接、改密码、持久运行和卸载步骤见[使用指南](docs/macos-remote-desktop/guide.md)。

## server-mihomo-codex

**用途：** 在无图形桌面的 Linux 服务器安装/修复 Mihomo、导入订阅、选择可用代理节点、配置用户后台服务和终端环境，并安装 Codex、验证 ChatGPT 订阅登录链路。适用于 SSH 和个人目录部署，不接管共享系统代理。

**在哪里使用：** Agent 在目标 Linux 服务器运行，或在本地通过用户已有 SSH 方式执行远端配置。官方下载、离线校验和上传可在有外网的本地机器完成。

**人类需要提供：** 已能使用的 SSH 别名/完整连接方式，以及私密的 Mihomo/Clash 订阅或完整配置。可选期望出口国家、持久运行需求和登录方式；默认当前普通用户，端口自行探测，登录由用户在浏览器完成。无需提供私钥内容、网站密码；订阅不进入仓库。

**安装示例：**

```bash
# 在要调用 Agent 的机器上；位于本仓库根目录，目标已存在时先比较/备份
cp -R skills/server-mihomo-codex "${CODEX_HOME:-$HOME/.codex}/skills/"
```

**调用示例：**

> 使用 $server-mihomo-codex，连接 `my-server`，为当前用户配置 Mihomo 订阅代理、用户后台服务和每次 Bash 登录的出口检查。优先美国节点，再安装 Codex 并验证登录接口；ChatGPT 网页授权由我自己完成。

**产物与影响：** 用户目录内的 Mihomo/Codex 程序、私有订阅和代理环境配置、systemd 用户服务，以及备份后的 `.bashrc` source 行。默认仅回环监听、关闭 TUN；显式修改前保留已有配置。复用依赖时通常无须 sudo，系统缺失依赖或要求系统服务时需相应权限。用户服务 enable 不保证无人登录的开机运行。

**依赖、实测和限制：** Bash、curl、适配架构的 Mihomo、可用节点；后台服务优先使用 systemd 用户管理器，转换 YAML 按需使用解析器。2026-10-26 会话在 Rocky Linux 8.10 x86_64 实测安装、美国出口、两个 OpenAI 接口 HTTP 200 和登录自动提示；账户授权由用户自行完成，未验证真实模型请求和跨重启持久性。新代理检查脚本另有隔离模拟测试。完整流程见[使用指南](docs/server-mihomo-codex/guide.md)，证据和范围见[验证记录](docs/server-mihomo-codex/validation.md)。

## 仓库结构

```text
River_Skills/
├── README.md                         # 全部技能的目录与使用入口
├── AGENTS.md                         # Agent 维护规则
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md                   # 技能入口，可独立安装
│       ├── agents/                   # 可选的 Agent UI 元数据
│       ├── scripts/                  # 该技能实际依赖的工具
│       └── references/               # 该技能运行时所需的参考文档
├── docs/<skill-name>/                # 面向人类的指南与验证记录
├── tests/<skill_name>/               # 按技能隔离的测试
└── scripts/check_repository.py       # 仓库结构、目录与文档链接检查
```

技能运行所需的资源应保留在自己的 `skills/<skill-name>/` 中；`docs/` 和 `tests/` 用于说明及维护，不是安装依赖。

## 维护与检查

新增技能前先检查现有技能是否已覆盖该用途。新增技能必须同步更新 README 的目录和详细说明，并记录实际验证范围，不能把尚未测试的平台写成已经支持。

```bash
# 仓库根目录：跨平台的结构、技能名称、目录与 Markdown 链接检查
python3 scripts/check_repository.py

# Linux 服务器：当前技能的自动检查，需要 Python 3.8+ 和 libgcrypt
python3 -m unittest discover -s tests -v
bash -n skills/macos-remote-desktop/scripts/mac-connect.sh \
  skills/macos-remote-desktop/scripts/prepare-debian-runtime.sh
```

实机集成测试的依赖、命令及清理行为见[桌面技能指南](docs/macos-remote-desktop/guide.md)。不在普通文档修改中启动真实桌面、安装系统依赖或改动已有服务。
