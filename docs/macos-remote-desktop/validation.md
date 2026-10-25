# 验证记录

验证日期：2026-10-25。环境：Ubuntu 22.04、x86_64、XFCE 4.16、TigerVNC 1.12、已安装的 Google Chrome，以及正常运行的 systemd 用户管理器。

## 已运行并通过

1. Skill Creator 的 `quick_validate.py`：技能命名、frontmatter、脚手架检查通过。
2. Python 模块编译和两个 shell 脚本的 `bash -n` 检查通过。
3. 17 项自动检查通过，覆盖：
   - dry-run 不创建文件；
   - 重复部署保留密码、显示号和配置，控制命令可执行；
   - 不覆盖不属于技能的命令和非空目录；
   - 活动会话拒绝配置变更，原配置可幂等重跑；
   - 更换显示号同步更新 Xauthority，保留密码；
   - 桌面隔离环境下仍能找到实际服务路径；
   - 拒绝代理 URL 中的凭据和 shell 注入形式的 SSH 目标；
   - 显示号冲突时选其他空闲值；
   - 浏览器 profile 隔离且保留浏览器沙箱，不启动浏览器的选择在重跑时保留；
   - 标准 DES 已知测试向量与往返解密；
   - 拒绝公网 VNC 监听；
   - Mac 助手复用别名、读取实际远端端口、打开正确 URL、只清理自己的隧道；
   - 本地端口占用/SSH 失败/非法目标不会错误打开屏幕共享。
4. `integration_vnc.py` 实际启动临时 VNC，完成 RFB 3.8、VncAuth challenge-response、640×480 完整 framebuffer 和 PNG 保存；进程与临时凭据随测试清理。
5. `integration_desktop.py` 实际生成独立配置及控制命令，检查 systemd unit 语法，在唯一临时用户服务中启动 XFCE 和 Chrome，通过 X11 确认窗口管理器与 Chrome 窗口，完成 800×600 framebuffer 认证/截图；随后停止临时单元、清理进程组及文件。
6. 扫描仓库源码：未包含本次私有主机/IP、账号、密钥路径、代理端口、运行生成的凭据或浏览器 profile。

## 没有声称已验证

- Mac 助手的控制流在 Linux 上使用模拟的 `ssh`、`nc`、`open` 等命令检查；没有在真实 macOS/Bash 3.2 上运行整套自动助手。实现仅使用 macOS 自带 Bash 可用语法及系统命令。
- 当前服务器的认证/画面验证不能证明任意 Mac 的 SSH 别名、私钥、跳板机和网络可达，也不能替代用户首次在 Mac 上实际登录。
- 没有为验证而在现有主机上重新安装系统桌面包；apt 用户目录回退应在目标 Debian/Ubuntu 的已配置软件源及实际依赖下核对。
- 其他 Linux 发行版、Snap 浏览器、容器无 systemd、音频/GPU/文件拖放没有列入本次实测范围。

上述限制已对应写入技能和用户说明。测试不改变现有桌面、不启用 lingering、不开放公网端口。
