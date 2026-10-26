# 验证记录

## 本次会话实测（2026-10-26）

环境：Rocky Linux 8.10 x86_64、Bash、普通用户、SSH、systemd 用户服务；私人主机、账号、订阅及节点凭据均不纳入仓库。

- Mihomo v1.19.33 官方兼容构建下载，经 release digest SHA256 校验并上传，远端再次校验，版本和配置检查通过。
- Codex CLI 0.164.0 Linux 原生平台包经 npm 元数据 SHA512 校验安装，版本、帮助、PATH 与配套 ripgrep 检查通过。
- 订阅包含 16 个节点；最终恢复 DNS 并选择硅谷节点，Cloudflare trace 返回美国出口。
- 普通组和 OpenAI 专用组选择一致后，auth.openai.com 的 OpenID 配置接口和 chatgpt.com/robots.txt 均返回 HTTP 200。
- `.bashrc` 代理变量及交互式出口检测配置完成，交互式登录 Shell 实测显示美国出口提示。
- 用户明确选择自行登录。只验证到 `codex login status` 尚未登录；没有替用户完成账户授权、没有真实模型请求验证。
- 未验证全登出/主机重启后持久性。Ubuntu/Debian、ARM64、系统级服务、其他订阅没有在本次会话部署验证。

以上是本次会话已完成的操作记录，不表示从仓库运行了完整自动部署；本次整理源码时没有重新部署或更改远端服务。

## 失败与修正

早期关闭订阅 DNS 后的系统解析测试失败，被过早解释为平台出口限制；该结论没有充分证据。恢复可用 DNS 后实际代理连通，说明应先保留/诊断应用自己的解析链路。

普通站点可访问后 OpenAI 仍失败，因为专用代理组选择不同；统一选择后两个 OpenAI 路径返回 200。延迟测试也曾使用不适合的目标，不能将其全失败当作所有节点故障的证明。

整理后的指南保留这些教训，但没有把会话中临时删除规则、测试 IP URL、变更所有代理组等操作作为通用默认。

## 仓库维护验证

- `python3 scripts/check_repository.py`：检查技能结构、README 清单和本地链接。
- `bash -n skills/server-mihomo-codex/scripts/proxycheck.sh`。
- `python3 -m unittest discover -s tests/server_mihomo_codex -v`：使用临时 curl 替身验证强制代理、地区判断、三次重试、超时/错误和非交互静默；不使用真实凭据、不连接实际代理。
- skill-creator 的 `quick_validate.py`：已通过（隔离临时虚拟环境补齐 PyYAML，没有修改系统 Python）。

脚本模拟测试不证明网络可达；OpenAI HTTP 200 不证明 ChatGPT 订阅权益或模型推理可用。未来部署应重新取得当次验证证据。
