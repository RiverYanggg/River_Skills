# 安装、订阅、后台服务与终端

所有安装命令在目标服务器执行，除非明确标注“本地”。示例假设 Bash；`REMOTE`、软件版本和端口由实际环境确定。个人安装布局可用 `~/.local/opt/<tool>/<version>/`、`~/.local/bin/`，配置 `~/.config/mihomo/`。已有部署优先复用，不硬覆盖同名文件/软链接。

## 1. 基线与官方下载

```bash
# 服务器
uname -srm
cat /etc/os-release
printf 'SHELL=%s\n' "$SHELL"
command -v mihomo codex node npm curl
ss -ltn
systemctl --user is-system-running
```

- Mihomo：[官方发布](https://github.com/MetaCubeX/mihomo/releases)。依据 `uname -m`、CPU 和 release 实际资产选择 linux-amd64-compatible、amd64-v1 或 arm64，不猜文件名。会话使用过 v1.19.33，未来执行时查询 release，不将其永久当成最新版。
- 在本机读取 release API 的资产 URL/digest，下载包并按官方 SHA256 校验。下载失败先区分域名解析、HTTP2、代理和实际 HTTP 状态；需要时改 HTTP1.1 或官方 GitHub release asset API，不改用未知镜像。
- 服务器不能下载时：本机下载 → 校验 → `scp` 上传 → 远端校验。长下载结束且校验通过后再解包；不对尚在下载的文件判断损坏。

```bash
# 服务器；已上传并校验的包命名为 mihomo.gz，版本按实际替换
mkdir -p "$HOME/.local/opt/mihomo/VERSION" "$HOME/.local/bin"
gzip -dc mihomo.gz > "$HOME/.local/opt/mihomo/VERSION/mihomo"
chmod 755 "$HOME/.local/opt/mihomo/VERSION/mihomo"
# 确认 ~/.local/bin/mihomo 不存在或属于本次部署，再创建/更新软链接
ln -s "$HOME/.local/opt/mihomo/VERSION/mihomo" "$HOME/.local/bin/mihomo"
export PATH="$HOME/.local/bin:$PATH"
mihomo -v
```

把缺失的 PATH 添加到现有 Shell 设置中，先检查是否已有相同设置。不要求 root；共享系统缺少必要依赖时报告具体依赖。

## 2. 下载和导入订阅

先创建权限 700 的配置目录。订阅下载到同目录临时文件，成功后验证为完整 Clash/Mihomo 配置，再原子替换配置；失败不得用 HTML 错误页或空文件覆盖工作配置。完整配置与只含节点的 provider 文档不同；后者需要代理组与规则包装。

优先通过工具的结构化参数传递 URL；Shell 中从用户终端安全读取：

```bash
# 在可联网的本机或服务器；不要打开 set -x
umask 077
read -r -s -p '订阅 URL: ' subscription_url
printf '\n'
case "$subscription_url" in
  https://*) ;;
  *) unset subscription_url; printf '仅接受 HTTPS 订阅\n' >&2; exit 1 ;;
esac
if [[ "$subscription_url" == *$'\n'* || "$subscription_url" == *$'\r'* ||
      "$subscription_url" == *'"'* || "$subscription_url" == *'\'* ]]; then
    unset subscription_url
    printf '订阅链接包含不支持的字符\n' >&2
    exit 1
fi
# curl 从 stdin 读取 URL，避免在 curl 进程参数里暴露链接。
# 仅接受已确认的 HTTPS 链接，拒绝包含引号、反斜线或换行的输入再拼接配置。
printf 'url = "%s"\n' "$subscription_url" | \
  curl --config - --fail --silent --show-error --location \
  --proto '=https' --proto-redir '=https' \
  --connect-timeout 15 --max-time 60 -A 'mihomo' -o subscription.yaml
unset subscription_url
```

输入检查在发起请求前执行。工具策略不允许直接传敏感 URL 时，使用该环境提供的私密文件/凭据输入方式。不要要求把真实订阅加入仓库。

备份已有配置，保留其 `dns`、`proxies`、`proxy-groups`、`rules`。普通 YAML 合并使用可用的 YAML 解析器，不用正则重写嵌套结构；Python 缺 PyYAML 时可在可联网机器解析后传输 JSON（Mihomo 可将 JSON 作为 YAML 子集读取），不因远端没包管理器而放弃。

示例字段（端口按探测结果替换，7890 只是示例）：

```yaml
mixed-port: 7890
allow-lan: false
bind-address: 127.0.0.1
mode: rule
log-level: info
ipv6: false
external-controller-unix: /absolute/home/USER/.config/mihomo/controller.sock
tun:
  enable: false
```

Unix socket 路径必须是实际绝对路径，目录权限 700；不依赖 YAML 展开 `~`、`$HOME` 或 `%h`。若选 TCP 控制接口，先检查空闲端口，使用 `127.0.0.1:PORT` 和随机 `secret`，不要公网监听。

保留订阅的 DNS 优先。若系统 DNS 不能解析节点，可针对 `proxy-server-nameserver` 配置可达的 bootstrap DNS；不要为避免下载地理数据库而直接关闭 DNS。按需要使用 `redir-host`、禁用 IPv6，但只在证据支持时调整。GEOIP/GEOSITE 需要的数据库应从可信来源获取，不能为了通过配置检查静默删除分流规则。

```bash
# 服务器
chmod 700 ~/.config/mihomo
chmod 600 ~/.config/mihomo/config.yaml
mihomo -t -d "$HOME/.config/mihomo" -f "$HOME/.config/mihomo/config.yaml"
```

## 3. systemd 用户服务

仅在 `systemctl --user` 实际可用时使用；先核对现有同名服务归属，端口冲突时区分其他用户/其他机器，不杀占用者。

```ini
# ~/.config/systemd/user/mihomo.service
[Unit]
Description=Mihomo personal proxy
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/mihomo -d %h/.config/mihomo -f %h/.config/mihomo/config.yaml
Restart=on-failure
RestartSec=3
UMask=0077

[Install]
WantedBy=default.target
```

```bash
# 服务器
systemctl --user daemon-reload
systemctl --user enable --now mihomo.service
systemctl --user is-active mihomo.service
ss -ltn
journalctl --user -u mihomo.service -n 50 --no-pager
```

启动后等待端口就绪再探测，避免“service active 但端口尚未监听”的竞态。journal 不可读时，可用当前 systemd 支持的文件日志输出，日志也按私有数据管理；不公开节点、凭据、订阅、完整日志。

用户服务依赖用户管理器；跨登出/重启持久运行需验证实际策略。仅在明确需要且有授权/权限时启用 linger；无用户管理器则给出前台运行方案及断开限制。用户要求系统服务且有 sudo 时，可按实际账号/路径建立系统 unit，不把本次普通用户方案升级成 root 进程。

## 4. 选择和持久化节点

通过受保护的 Mihomo 控制 API，或修改代理组默认首项选择用户期望节点。核对 OpenAI 专用组与普通组是否不同，不能只测默认组然后宣布 Codex 可用。对于控制 API 选择，验证重启后保存情况；若使用组首项方案，核对 `profile.store-selected` 及旧缓存是否覆盖新默认。

保留订阅中已有组和节点。不要因为改一个组就往所有组加入不相关节点。订阅更新后重新检查组内引用、DNS 和选择持久性。

## 5. 终端代理与交互式自动检查

将代理变量放入权限 600 的 `~/.config/mihomo/proxy-env.sh`，填入实际监听端口：

```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy="$http_proxy"
export HTTP_PROXY="$http_proxy"
export HTTPS_PROXY="$https_proxy"
export all_proxy=socks5h://127.0.0.1:7890
export ALL_PROXY="$all_proxy"
export no_proxy=localhost,127.0.0.1,::1
export NO_PROXY="$no_proxy"
# 可选：用户要求固定美国出口时设置；不设置则接受任意有效国家码。
export MIHOMO_EXPECTED_COUNTRY=US
```

保留原有内网 no_proxy 条目，不凭示例清空用户已有设置。将技能内 `scripts/proxycheck.sh` 复制到同目录，权限 600。备份 `.bashrc` 后仅添加缺失的 source 行：

```bash
# ~/.bashrc；代理变量先加载，检查脚本后加载
[ -f "$HOME/.config/mihomo/proxy-env.sh" ] && . "$HOME/.config/mihomo/proxy-env.sh"
[ -f "$HOME/.config/mihomo/proxycheck.sh" ] && . "$HOME/.config/mihomo/proxycheck.sh"
```

脚本仅交互式自动运行，最多三次，每次最长五秒；显式指定代理且关闭 no_proxy 绕过。它检测出口，不启动服务、不切节点、不验证 OpenAI 授权。确认已有 `.bash_profile` 会加载 `.bashrc`，避免重复 source。

```bash
# 服务器：当前交互式终端
source ~/.bashrc
proxycheck
```

systemd 服务不自动读取 Bash 环境；为需要代理的独立服务单独设置 Environment/EnvironmentFile，不能将 Shell 的 `export` 文件直接当 systemd EnvironmentFile 使用。共享 HOME 不代表代理进程运行在所有登录节点：多登录节点平台应逐主机核对 `hostname` 和本机端口，不把一台机器监听当作全平台已启用。

## 6. Codex 与订阅登录

官方入口：[CLI](https://developers.openai.com/codex/cli/)、[认证](https://developers.openai.com/codex/auth/)。按执行时可获取的官方说明和已安装 CLI 帮助核对命令；不要猜当前版本或账号权益。

有 Node/npm 时可使用官方 npm 安装方式；无 Node 时优先官方 release 原生二进制。也可由 npm registry 的 `@openai/codex` 元数据定位与版本匹配的平台包：

1. 获取主包和平台变体元数据，不硬编码未来的包名/架构布局。
2. 根据 `dist.integrity` 用 SHA512 校验平台 tarball，上传后再次校验摘要。
3. 解包到版本目录；先查看资产布局。保留 `vendor/<target>/` 里的配套资源，不只复制主程序。
4. 从 `~/.local/bin/codex` 指向实际原生程序，保留现有安装可回滚。不要用假定的 musl 路径覆盖其他架构。

```bash
# 服务器；加载代理后再登录
source ~/.config/mihomo/proxy-env.sh
codex --version
codex login --help
codex login --device-auth
# 用户在自己的浏览器按提示完成 ChatGPT 账号授权后
codex login status
```

用户选择订阅时不切换 API Key、不复制其他主机的 auth.json。设备码属于短期认证信息，不发布到仓库；用户要求自己登录就只交付命令。必要时按当前官方说明使用 localhost 回调的 SSH 转发登录；设备授权不可用不代表应该换成 API 计费。
