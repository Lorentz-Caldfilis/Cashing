# Cashing 状态快照

## 2026-10-01 1.2.0 背景移除更新

已移除背景导入、绘制、恢复默认菜单和实现模块，恢复固定浅色界面，保留用途选择与图标；应用及 Windows 版本资源继续为 1.2.0。旧私人背景文件不读取、不改写、不自动删除，忽略规则和打包拒绝检查保留。

本机隔离完整回归 **412 passed、2 skipped / 193.76s**（跳过项为主机不允许创建文件系统链接）；报告 `work/remove-background-20261001/tests.xml` 与 `tests.txt`。新增回归验证遗留损坏背景不影响启动/保存并原样保留。源码、最终 EXE 和 ZIP 解压副本各五次原生 GUI 流程通过，冻结/解压各 430 个 manifest 文件、默认路径两次启动持久化和安装目录不变通过；报告 `work/remove-bg-source-01/`、`work/remove-bg-frozen-01/`、`work/remove-bg-extracted-01/`。本机为明确的 parser 剪贴板限定模式，不能算系统剪贴板通过。

[Windows CI](https://github.com/Lorentz-Caldfilis/Cashing/actions/runs/36864737317) 精确 head `5c876ad58269089d4878a0f6a597dbab50f8eeda` **success**：**414 passed、0 skipped / 72.65s**；源码与解压 EXE 各五次原生 GUI，均为 system 模式，含真实剪贴板、用途、固定浅色界面、图标、重启和缩放。解压 397 个 manifest 文件核对及默认路径重启通过。原始日志与 JUnit/GUI 报告保存在 `work/remove-background-20261001/ci-36864737317.txt`、`ci-evidence/`。[PR #3](https://github.com/Lorentz-Caldfilis/Cashing/pull/3) 已合并，合并提交 `ab6984294c784a53cb4660476dddd5317013af7b`，合并树与上述真实构建源码完全一致；本机 main 已同步。

本机入口仍为 `运行Cashing.bat` / `测试Cashing.bat`，均使用新版 `release/Cashing-v1.2.0-windows/Cashing/Cashing.exe`；自动验证未打开正式或既有手动试用账本。原包完整另存到 `release/previous-v1.2.0-with-background-b89610d76b1c/`，原标签/资产/说明及旧 ZIP 摘要记录在 `work/remove-background-20261001/previous-*.json`。新包仍包含 MIT、原始第三方许可、对应源码归档及构建清单。

[v1.2.0 Preview](https://github.com/Lorentz-Caldfilis/Cashing/releases/tag/v1.2.0) 同名 ZIP 与摘要已更新，非 draft、prerelease；标签及真实构建来源均为上述 `5c876ad`。EXE SHA-256 `95bb73ea7b24a33641b0b97cabb42b35f59891651496983a0a03368ae9640e8d`；ZIP `fbb781063d7f3ccbfcd6c6090df81a6e8e5fb30ee3c7721ec5ff818afc461e12`，服务器 asset digest 与本机一致，远端记录 `work/remove-background-20261001/updated-release.json`。本次同版本预发行替换由所有者明确授权，使用新摘要区分；仓库仍 private，MIT 及公开准备边界保持，未声称完成代码签名或人工设备验收。以下首次交付的测试和摘要仅作历史证据。

## 2026-10-01 1.2.0 首次预发行与公开准备（背景移除前历史）

本轮已实现时间下方可选的生活/工具/娱乐用途，选择来源、草稿、保存失败保留及撤销一致；本地图片背景原子复制、两页共用阅读层及恢复默认；二次元极简窗口/任务栏/EXE 图标。应用及 Windows 版本资源更新为 1.2.0。分类准确性和进一步 UI/操作优化仍为持续开发项。

所有者已授权本轮提交、推送和合并，以及选择开源许可证。根目录 MIT 署名 © 2026 Lorentz-Caldfilis，免费使用/修改/分发须保留版权和许可。新增贡献者保留各自版权。第三方依赖的授权、对应源码归档、摘要与动态库替换说明已准备，仓库继续保持私有。

本机完整回归 **411 passed、2 skipped**；新增对应源码防篡改测试及定向 UI 回归 **18 passed**。源码五个原生 Windows GUI 流程在明确的 `parser` 模式下通过：系统剪贴板 Win32 OpenClipboard 返回 error 5（拒绝访问），该模式只验证合成粘贴解析，不能算真实系统剪贴板通过。报告 `work/v120-source-limited-01/verification.json`。GitHub CI 保持真实系统剪贴板为默认门槛。

全远端 refs 可达历史模式扫描及 23 张图片复核完成；未见私钥、令牌、SQLite 数据或私人截图。人工设备验收仍见 MANUAL_ACCEPTANCE.md。

**合并与完整远端门槛：** [PR #2](https://github.com/Lorentz-Caldfilis/Cashing/pull/2) 已合并，合并提交 `841fd3ee232b398808b0dde292570db1e6cf5202`，本机 main 已同步。精确 head `86742a3715a8dbc93dc8707ac8d4e10e2aab9c59` 的 [Windows CI](https://github.com/Lorentz-Caldfilis/Cashing/actions/runs/36858045053) **success**：415 passed、0 skipped；源码与解压 EXE 各五次 system 模式真实 GUI 流程通过，含用途、背景、图标、真实剪贴板、键盘、重启和缩放。解压安装 397 个 manifest 文件核对与默认数据路径重启通过。合并提交的 Git tree 与已验收 head 完全一致。

**本机冻结证据：** 提交 `86742a3` PyInstaller 构建成功，EXE 版本/版权资源核对通过。候选 ZIP `585924d0f158559bf71e1bcc0341ca4c0ace21618a4e13b84b401ffc9897e3c1`，430 个 manifest 文件。原候选目录与 ZIP 解压副本均通过五次 parser 模式流程、默认路径两次启动及安装目录不变检查（`work/v120-frozen-limited-02/`、`work/v120-extracted-limited-01/`）。第一次原目录验收在返回 Capture 的焦点断言失败，第二次串行重验通过；失败记录保留，不能声称全部尝试无失败。本机系统剪贴板仍没有通过，完整该项证据来自上述 Windows CI。

**公开前旧资产：** v1.0.0/v1.1.0 ZIP 和页面元数据已在隔离目录备份，摘要/CRC 通过，未发现账本/草稿/日志；旧包存在未使用 VirtualKeyboard 插件且许可交付不完整，因此转为私有 draft，保留原资产与标签，公开后不作为公众发行。9 个旧 CI 二进制候选已按名单清除，保留测试证据和本轮含对应源码的候选，不把历史包重命名冒充新版本。

**最终交付与公开：** 从 main 的 `b89610d76b1c7d685a7deb5a81ad0781d86ebd57` 构建 `release/Cashing-v1.2.0-windows/Cashing/Cashing.exe` 及完整 ZIP，包含 MIT、第三方原始授权、四份对应源码归档、依赖/构建身份及 430 个 manifest 文件。最终原目录和解压目录各五次 parser GUI、默认路径两次启动及安装完整性通过，报告 `work/v120-delivery-frozen-01/`、`work/v120-delivery-extracted-01/`。根目录本地运行/测试入口均已改用 1.2.0，未打开正式账本。

[GitHub v1.2.0 Preview](https://github.com/Lorentz-Caldfilis/Cashing/releases/tag/v1.2.0) 已上传 ZIP 与摘要，非 draft、prerelease；标签指向上述真实构建提交。EXE SHA-256 `ce371ce7ca1ce6f062c4693a5fa96b60266437a43487d9f8b3f0bd624ce0a873`；ZIP `31141c6aa46b0ff4505499feb6790f9ad8a7749711010610a87477778a256db7`，GitHub 服务器 asset digest 与本机一致。仓库仍为 **private**，默认分支 main，GitHub 已识别 MIT；所有者可直接切换公开，使当前源码与该预发行包公开可取。代码签名和人工设备体验不声称完成。

交付构建提交 `b89610d` 的可达历史扫描为 639 个 blob、25 个 PNG/JPEG 图片 blob，无私钥/令牌/数据库命中，唯一 home 路径命中为审计正则；新增 PNG 是已查看的生成图标及缩放版本，ICO 来源同图。既有本机 stash、未跟踪记录、旧发行副本与个人 Hook 均保留本机。

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
