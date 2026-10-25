# River_Skills

RiverYanggg 的可复用 Agent 技能库。每个技能说明用途、执行位置、所需输入、安装方式、验证范围和操作边界，让新服务器上的 Agent 可以直接接手。

## 技能目录

| 技能 | 用途 | 主要执行位置 | 人类需要提供 | 使用文档 |
|---|---|---|---|---|
| [macos-remote-desktop](skills/macos-remote-desktop/SKILL.md) | 为 Linux 建立独立 XFCE/TigerVNC 桌面，Mac 使用自带“屏幕共享”连接 | Linux 服务器；Mac 负责 SSH 隧道和查看桌面 | Mac 已能使用的 SSH 别名；目标用户默认当前用户；可选浏览器、代理、分辨率及持久运行需求 | [完整指南](docs/macos-remote-desktop/guide.md) · [验证记录](docs/macos-remote-desktop/validation.md) |

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
