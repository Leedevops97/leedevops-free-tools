# Leedevops 免费开源工具

第一款工具 **Server Lens 1.0.0**：单文件 Linux 服务器状态检查工具，MIT 许可，
永久免费获取，无需注册或付款。终端界面默认英文，使用 ASCII 字符兼容普通 SSH 终端。

## 使用

解压下载包后，在终端运行：

```sh
sh tools/server-lens/server-lens
sh tools/server-lens/server-lens --watch --interval 5
sh tools/server-lens/server-lens --json
sh tools/server-lens/server-lens --json --redact
```

无需安装 Python、Node、Docker，也不会安装任何软件或常驻进程。普通用户即可运行。
如需要查看受保护的登录日志，可自行选择 `sudo sh tools/server-lens/server-lens`。
退出刷新按 Ctrl+C。不执行自动修复、不修改时间、不主动访问互联网、不上传数据。
可选时间客户端查询本机时间服务时，可能使用本地套接字或回环连接。

检查项包括：最近登录及时间、当前 utmp 会话、CPU 一秒采样及负载、内存和交换空间、
磁盘占用、系统时间和已配置时间服务的同步证据，以及可读取的容器资源限制。

## 如何理解结果

- 时间 `synchronized` 表示本机时间客户端报告已同步，不是独立对比互联网时间。
  仅开启 NTP 不算同步。本地参考钟单独标为 `local-reference`。
- 没有日志权限、缺少命令或记录已轮转时，结果会标为不可用／无法确认，不能据此认定没人登录。
  日志回退只覆盖最近有限范围内成功的 SSH 登录；旧版 last 日期精度可能有限。
- 容器内 `/proc` 的 CPU 和内存可能属于宿主机，容器限额另外列出；不完整推算嵌套 cgroup 配额。
- CHECK/HIGH 分别为 80%/95% 的简单使用率提示，不等同于故障诊断。
- `--redact` 会隐藏主机名、完整登录记录及文件系统路径。公开报告前仍需自行检查。
  需要保存未脱敏报告时先执行 `umask 077`，避免报告被其他用户读取。

支持范围和实测环境见 [TESTING.md](TESTING.md)。该工具是基础状态快照，不是完整安全审计系统。

维护及反馈：[lx.iwtfree@gmail.com](mailto:lx.iwtfree@gmail.com)。
