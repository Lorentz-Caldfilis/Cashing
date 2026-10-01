# Cashing 状态快照

## 2026-10-01 1.2.0 与公开准备

本轮已实现时间下方可选的生活/工具/娱乐用途，选择来源、草稿、保存失败保留及撤销一致；本地图片背景原子复制、两页共用阅读层及恢复默认；二次元极简窗口/任务栏/EXE 图标。应用及 Windows 版本资源更新为 1.2.0。分类准确性和进一步 UI/操作优化仍为持续开发项。

所有者已授权本轮提交、推送和合并，以及选择开源许可证。根目录 MIT 署名 © 2026 Lorentz-Caldfilis，免费使用/修改/分发须保留版权和许可。新增贡献者保留各自版权。第三方依赖的授权、对应源码归档、摘要与动态库替换说明已准备，仓库继续保持私有。

本机完整回归 **411 passed、2 skipped**；新增对应源码防篡改测试及定向 UI 回归 **18 passed**。源码五个原生 Windows GUI 流程在明确的 `parser` 模式下通过：系统剪贴板 Win32 OpenClipboard 返回 error 5（拒绝访问），该模式只验证合成粘贴解析，不能算真实系统剪贴板通过。报告 `work/v120-source-limited-01/verification.json`。GitHub CI 保持真实系统剪贴板为默认门槛。

全远端 refs 可达历史模式扫描及 23 张图片复核完成；未见私钥、令牌、SQLite 数据或私人截图。构建、冻结/解压验收、远端 CI 和合并尚待执行，本段不预写完成。人工设备验收仍见 MANUAL_ACCEPTANCE.md。

## 2026-10-01 本机更新（本轮修改前的历史）

本地已按本人选择切换至远端开发分支 `codex/student-edition-20260930` 的 `90b18df8f4976c745db512496a2f3ce2440af8f4`。这是尚未合并的 PR #2 开发候选，应用版本资源仍为 1.1.0；main 与正式 Release 未改变。本次未提交、推送或发布。

本机依赖检查通过；原生 Windows Qt 源码测试 **404 passed、2 skipped**（测试所需的文件系统链接创建不被本机允许）。源码五个 GUI 进程验收通过。候选包和 ZIP 解压副本的 434 个清单文件、ZIP CRC/摘要、隔离默认路径及重启持久化通过。冻结版独立烟测通过，但多次完整冻结 GUI 验证在启动/草稿焦点、粘贴或快捷键撤销断言处失败，原因未确定；**冻结 GUI 完整验收未通过**，不能用独立通过记录覆盖失败。

使用入口为根目录 `运行Cashing.bat`（默认个人账本），测试入口为 `测试Cashing.bat`（独立的 `work/student-manual-20261001` 账本）。程序位于 `release/Cashing-candidate-90b18df8f497-windows/Cashing/Cashing.exe`。旧 v1.1.1 发行物保留。原未提交 tracked 内容保存在命名 stash，文件备份位于 `work/github-update-20261001/local-backup/`；本轮自动验证未打开正式账本。

原有类别匹配及 UI/操作优化诉求仍需本人真实试用复核，新实现与合成回归不等于诉求已全部完成。本机隔离记录保留在 `work/github-update-20261001/`。以下内容保留为原分支历史证据。

## 2026-09-30 开发候选

独立分支 `codex/student-edition-20260930`，main 基线 `ebd0c8b`，草稿 [PR #2](https://github.com/Lorentz-Caldfilis/Cashing/pull/2)。
应用改动 `a0d6b95`，最终烟测/构建源码 `62cff8f`，后续 docs/evidence 提交不改变应用行为。未改 main、许可或发布资产。
Linux 406 tests / 36.32s，独占 X11 的 100%、重启、125%、150%、200% 五个 GUI 进程通过。
Windows `62cff8f`：406 tests、5 source + 5 extracted GUI、401 hashed files 加 manifest、默认路径重启均通过。精确源码结果见 [启动与最终旅程报告](development/STARTUP_AND_JOURNEY.md)。

原子草稿、单笔粘贴、可逆学习/纠错、本地备份、来源显示、分页完整统计与构建来源验证均已具备。
固定 DEV/holdout 明确用途覆盖 12/12、6/6，原版 C1/C2 15/15、23/23；均为已知合成回归而非真实准确率。
旧模拟器的覆盖退让保留在 [第四阶段记录](development/STUDENT_PHASE4.md)。
1 万条有界性能/新目录恢复与分页审查修复见 [耐用性记录](development/STUDENT_DURABILITY.md)。
新用户录入→学习→撤销→搜索→备份→恢复旅程已有实际 GUI 截图；启动仍存在本环境首次 Qt 子窗口约 3s 等待。

最有价值的剩余事项：最终独立复核、真实 Windows IME/触控板/跨屏/物理离线与干净设备、
所有者的开源许可和第三方再分发决定。Library 上传认证失败已停止重试，截图在 repo 中。
本轮未重核历史 Release 资产；以下 2026-09-27 快照仅为历史，不作为本分支发布证据。

---

**核对日期：** 2026-09-27。此页是可更新的快照；不能把它当成长期不变的设计约束。稳定规则见 [PRODUCT.md](PRODUCT.md)和 [MAINTENANCE.md](MAINTENANCE.md)。

## 版本与远端

- 本次文档维护前的源码基线：`08e333b7671a952d52c75f43a8338fe725be68d1`；核对时本地与 GitHub `main` / `HEAD` 一致。后续文档提交会推进 `main`，不改变此处记录的应用源码基线。
- GitHub 仓库：[`Lorentz-Caldfilis/Cashing`](https://github.com/Lorentz-Caldfilis/Cashing)，私有，默认分支 `main`，未归档；核对时无开放 PR。私有仓库页面需要访问权限。
- 最新 Release：[`v1.1.0`](https://github.com/Lorentz-Caldfilis/Cashing/releases/tag/v1.1.0)，已发布、非预发布。`v1.1.0` 注释标签指向上述提交。
- GitHub 发行资产 `Cashing-v1.1.0-windows.zip` 的服务器 SHA-256 与本地 ZIP 相同：`54f28cc138822d586c45a2bea04b84126e1d751dbbba7a594d6f50b40589f0db`。这证明本地 ZIP 与远端资产一致，不证明所有设备上的运行体验。

## 已实现

Windows PC Light 双空间 Capture / Review；金额、说明、时间的快速记录；月度汇总和按天历史；搜索、原地编辑、删除和撤销；独立草稿；仅存用户指定类别、读取时本地派生分类。Python + PySide6 + 标准库 sqlite3，schema v3，PyInstaller onedir 发行。Core 没有运行时网络依赖。

## 本次核对与尚未验证

- 本次执行源码测试：`237 passed`（`-W error`，Windows，隔离的 `work/pytest-maintenance-20260927`）。
- 本次执行 `scripts/verify_release.py`：源码和本地冻结版各 `PASS`，每个阶段启动 5 个原生 GUI 进程；报告分别在 `work/docs-20260927-source/verification.json`、`work/docs-20260927-frozen/verification.json`。冻结版检查还确认默认数据路径重启持久化及安装目录未变化；所有数据位于隔离的 `work/` 验收目录。
- 既有 `v1.1.0` 发行包与远端摘要相同。本次文档维护未重打包、未覆盖已发布资产。
- 分类精确率约 99%、覆盖率约 82–83% 是仓库中确定性**合成**基准的新用户第 6 个月结果，不是实际用户长期效果。
- 真实触控板方向与手感、中文 IME、跨显示器移动、Windows 10、未安装 Python 的干净机器、物理断网和长期大数据量仍需要分别验收。既有自动 GUI 与进程记录见历史实施文件；它们不能替代这些人工/环境验收。

## 维护时更新

修改此页时重新核对 `git status`、本地/远端 `main`、标签解引用、Release 元数据与资产摘要、版本字符串及实际测试输出。只记录本次真正运行过的检查；远端无法访问时标明仅为本地或历史证据。详细操作与数据安全规则见 [MAINTENANCE.md](MAINTENANCE.md)。
