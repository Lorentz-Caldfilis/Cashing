# Cashing v1.0.0 独立发布前审计

审计日期：2026-09-19。项目根目录：D:\Dev\Cashing。未增加业务功能。
本轮以现有源码为待审提交重新审查，并用新增回归与真实进程运行验证修复。

## EXE 事实核验

审计开始时找到两个 Cashing EXE：
- D:\Dev\Cashing\dist\Cashing\Cashing.exe
- D:\Dev\Cashing\build\Cashing\Cashing.exe

根目录没有 EXE。现有 dist 版经过真实启动，主窗口出现、验收流程 PASS、
退出码 0、stderr 为空，因此“之前不存在 EXE”与本轮实际检查不符。
但之前未提供醒目的正式发行入口和 ZIP，交付可发现性不足，已纠正。
全项目所有 EXE（包括虚拟环境的工具程序）完整绝对路径清单保留于
work/audit-exe-inventory.txt；工具 EXE 不能当作 Cashing 发行文件。

本轮正式发行目录：
D:\Dev\Cashing\release\Cashing-v1.0.0-windows\Cashing

正式 EXE：
D:\Dev\Cashing\release\Cashing-v1.0.0-windows\Cashing\Cashing.exe

发行 ZIP：
D:\Dev\Cashing\release\Cashing-v1.0.0-windows.zip

必须保留 Cashing 文件夹与 _internal；start.bat 只是开发辅助脚本。
EXE 的 FileVersion / ProductVersion 均为 1.0.0。

## 确认的问题与修复

| 问题 | 实际证据 | 修复 |
| --- | --- | --- |
| 初始化仅检查列名，错误字段类型仍被接受 | 同列名、amount_cents TEXT 的独立回归失败 | 检查类型、主键与 NOT NULL 属性 |
| 非法/非规范时间可能被当作正常记录或漏出月度查询 | 9 月 31 日、非补零、T 分隔、秒和时区后缀共 5 个失败案例 | 启动检查既有记录；读取也校验规范本地时间，报错而不改原值 |
| 初始化 DDL 不在显式事务内，索引冲突后留下 records 表 | 人为预置同名表造成索引失败，回归发现 records 仍存在 | BEGIN IMMEDIATE 包含完整建库流程；失败回滚 |
| 大缩放下最小窗口超过可用屏幕 | 像素比例 3.0 时窗口 900×600，可用区域 853×509 | 限制窗口尺寸并用滚动容器保持控件可达；修复后 813×449 |
| 调整说明列宽后行高未自动重算 | 原实现仅刷新数据时计算行高 | 单个防抖 QTimer 处理列宽变化，长说明仍可完整查看 |
| 验收模式使用正式账本同名文件，隔离保护不够直接 | 路径代码审查 | 独立 smoke-ledger.sqlite3；拒绝正式默认目录、含真实文件或未标记非空目录 |
| 自动验收只检查对象状态、部分直接调用保存逻辑 | 运行脚本审查 | 改为实际按钮、导航和键盘操作，检查可见主窗口、中文翻译、截图返回值、屏幕尺寸 |
| .gitignore 未包含 *.db、IDE 配置和凭证规则 | 文件审查 | 补充 SQLite 变体/日志/缓存/发行文件/凭证/IDE 忽略规则 |
| 发行入口不清楚，缺乏完整目录清单 | 用户反馈及根目录实际布局 | release 目录、ZIP、根目录“开始使用.txt”、版本信息、逐文件哈希及使用说明 |

未将浮点用于账单金额或月度合计。饼图比例使用浮点只用于显示。
未改变已有账单金额、类别、时间或业务数据，未删除真实数据库。

## 测试结果与中间失败

最终测试：**总数 100，通过 100，失败 0，错误 0，跳过 0，pytest warning 0**。
最终完整测试使用原生 Windows Qt 平台，耗时约 11.14 秒。
证据：work/audit-tests-final.log、work/audit-tests.xml。

中间失败没有隐去：
1. 修复前独立回归运行 **7 失败**，均复现上表前三类问题。
   证据：work/audit-before-fix.log；修复后 7 项全部通过。
2. 首轮扩大测试 **97 通过、3 失败**。
   一项是新增只读测试替身参数名与 sqlite3 uri 关键字冲突；
   一项是鼠标双击模拟缺少前置点击；遗留定时器又影响下一项菜单测试。
   已修复测试调用和定时器生命周期，未降低断言或跳过用例。
   证据：work/audit-tests-1.log。
3. 测试后一次附带构建命令拼写错误；独立执行正确 build.ps1 后构建成功。
   最终构建证据：work/audit-build.log。

新增覆盖包括：
- 金额边界、非法格式、0/负数/超大值；三类整数合计；
- 以 datetime 对象筛选的独立随机参照，共 120 笔合成数据；
- 非闰年/闰年二月及相邻月份隔离、年底、排序；
- 编辑/删除中途 SQLite 触发器中止，验证其他写入一并回滚；
- 只读 SQLite 连接、不可用父目录、连接关闭、错误数据；
- 中文、空格、#、% 路径，正式数据与验收数据隔离；
- 真实双击、菜单键盘选择、删除取消与失败、Enter 保存、Tab 顺序；
- 多次导航无重复保存和重复画布；
- 窄窗口长说明行高和窗口销毁后 Figure/Canvas 弱引用释放。

## 最终原生运行验收

环境：Windows 11 x64（10.0.26200）、Python 3.14.7、Qt/PySide6 6.11.2、
Matplotlib 3.11.2、PyInstaller 6.22.3。完整依赖见 requirements-lock.txt。

| 对象 | 真实进程验证 | 结果 |
| --- | --- | --- |
| 最终源码 | 5 次 GUI 流程，每次 25 项检查 | PASS |
| 正式发行目录 EXE | 5 次 GUI 流程 + 2 次普通默认模式启动/关闭 | PASS |
| 从 ZIP 全新解压到中文空格路径的 EXE | 5 次 GUI 流程 + 2 次普通默认模式启动/关闭 | PASS |
| 解压安装目录 NTFS 拒绝当前用户写入 | 写入探针实际被拒绝，EXE 全流程仍通过；最后恢复原 ACL | PASS |
| 特殊路径、改变工作目录、PATH 不含 Python | 实际启动与重启 | PASS |
| 像素比例 1.5 / 1.875 / 2.25 / 3.0 | 主界面、图表、滚动和可用屏幕尺寸 | PASS |
| 新增→查看→编辑金额与分类→删除→空月→跨年→重启 | 实际按钮、导航、确认对话框，持久化账单复核 | PASS |
| 中文 Qt 翻译、截图写入、主窗口可见 | 每轮显式断言 | PASS |
| 正常关闭与重启保留账单 | 默认模式使用真实窗口 WM_CLOSE，退出码 0 | PASS |
| 正式及解压目录 484 个文件哈希 | 运行前后相同，未生成数据库或日志到安装目录 | PASS |

最终共 **19 个源码/正式 EXE/解压 EXE 进程**完成上述验证。
所有最终进程 stderr 为空，无启动 traceback。
已查看真实渲染截图；测试不是仅 import 或构造页面。

机器可重复验证入口：
- scripts/verify_release.py
- scripts/verify_readonly.ps1

本地详细证据（不提交测试账本和缓存）：
- work/audit-source-final/verification.json
- work/audit-frozen-final/verification.json
- work/audit-readonly-extracted/verification.json
- work/readonly-install-result.json
- work/audit-summary.json

## 发行完整性

ZIP CRC 检查通过，ZIP 解压后 484 个文件逐项与 MANIFEST.sha256 一致。
程序安装目录只包含运行库、文档和许可证，不含测试或用户账本。
EXE SHA-256：
ac22557691b9efd6cae5eab8c78a2871248d98ae04a88cb727b24eec4efbaecf

ZIP SHA-256：
61333e03ea4c79423fb07b96f88f46d36a18319235e98c3aaf1be815ccd9ed1e

ZIP 大小：78,990,841 字节。配套校验文件为 Cashing-v1.0.0-windows.zip.sha256。
运行库、Matplotlib data、Qt Windows 插件、中文基础翻译均已通过实际启动验证。

## 数据和发布边界

正式数据：%LOCALAPPDATA%\Cashing\ledger.sqlite3。
源码、正式 EXE 与 ZIP 解压版使用同一规则，升级不复制或覆盖已有账单。
默认路径验证通过覆盖子进程 LOCALAPPDATA 到项目内模拟目录完成，没有访问真实账本。

本轮开始时没有 .git 或 remote，不存在需保留的项目 Git 历史。
发布目标是 Lorentz-Caldfilis/Cashing 私有仓库；源码进入 Git，
发行 ZIP 与校验文件进入 v1.0.0 Release，不提交 build/dist/release/work。
gh 身份与 repo 权限已经确认；提交前对 36 个暂存文件逐项扫描，SQLite/二进制文件 0 个、凭证模式命中 0 个；账单、虚拟环境、缓存、日志和发行目录均已实际确认忽略。历史内容还将在提交后、push 前复核。
GitHub 最终 commit、private 状态、Release 和上传结果以本轮最终交付回执为准。

## 需要人工验收及已知限制

- Windows 10 实机、未安装 Python 的干净 Windows 机器：**需要人工验收**。
  PATH 不含 Python 的实测不等同于干净机器。
- 真实中文输入法、系统日历的人工操作体验、跨显示器动态 DPI 切换：**需要人工验收**。
  固定缩放、键盘 Tab/Enter、鼠标双击及菜单选择已自动验证。
- 物理断网：**需要人工验收**。自动流程禁用 Python socket 连接/DNS，
  应用没有网络业务代码；未修改系统网卡或防火墙。
- 未做长期数月运行、突然断电、硬盘损坏、极大量记录压力测试。
- 无数字签名、自动备份或多人并发编辑冲突合并，未改变简化产品定位。
- 在本轮已验证范围内，没有仍未修复的阻塞核心使用问题。
