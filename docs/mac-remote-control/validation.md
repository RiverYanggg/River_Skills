# 验证记录：mac-remote-control

本文记录已完成的检查与实测范围。主机名、用户名、路径均已脱敏。

## 自动检查（仓库内，可重复）

- `python3 -m unittest discover -s tests -v`：包括 `tests/mac_remote_control/test_skill.py` 的 5 项检查，覆盖 frontmatter 与目录名一致、必需文件存在、技能文件不含私人标识、脚本语法、未配置别名且端口未监听时返回失败。
- `python3 scripts/check_repository.py`：技能清单、README 目录与本地链接。
- `bash -n skills/mac-remote-control/scripts/check-mac-tunnel.sh`：语法检查。

已知问题（仓库内既有测试，非本技能）：`tests/macos_remote_desktop/test_skill.py::MacHelperTests::test_ssh_failure_does_not_open_screen_sharing` 约 12% 的运行中失败（25 次中出现 3 次，断言 `open` 调用不存在时为 True）。本次提交未修改该测试，需单独排查。运行 `python3 -m unittest discover -s tests` 时可能因此报告 1 个失败，与本技能的 5 项检查无关。

## 服务器实测（2026-11-13，作者环境）

环境：Linux 服务器（Ubuntu 22.04，OpenSSH 8.9）；Mac 端为 macOS（Darwin arm64），系统自带 Python 3.9.6。

已验证：

1. Mac 通过 `ssh -R 2222:localhost:22 <服务器别名>` 建立隧道后，服务器 `127.0.0.1:2222` 处于监听状态。
2. 隧道建立但 Mac 端 sshd 未正常响应时，服务器 SSH 握手被重置（`Connection reset by peer`）。该现象已在实测中出现，并作为检查脚本的排错提示。
3. Mac 端开启远程登录并授权服务器专用公钥后，服务器通过 `mac-tunnel` 别名免密登录，`whoami`、`$HOME`、`uname -s` 返回预期值。
4. 通过别名在 Mac 上创建、运行并删除临时文件，成功。
5. 通过别名在 Mac 上创建 Python 测试脚本并运行，输出符合预期。
6. `scripts/check-mac-tunnel.sh` 在上述配置下输出 `RESULT: PASS`；在未配置别名、未监听端口的情况下输出 `RESULT: FAIL` 且退出码为 1。

## 未验证

- **sshfs 挂载**：服务器未安装 sshfs（需要 sudo 密码，无法非交互安装），因此 `references/setup.md` 第 7 节的挂载步骤只做了文档化，未实际执行。
- **Agent 通过挂载目录修改真实项目**：未测试。
- **其他 Mac 机型、其他 macOS 版本、Linux 或 Windows 作为本地端**：未测试。
- **隧道断开后的自动重连**：未测试，仅在文档中给出可选参数。
- **多台 Mac 共用同一服务器**：未测试，仅说明换端口的做法。

## 复现要点

真实环境检查需要 Mac 保持隧道窗口开启。没有隧道时，检查脚本会在第 1 步直接报告端口未监听，这是预期行为，不代表技能失效。
