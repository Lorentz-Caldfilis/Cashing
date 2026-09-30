# Cashing · PC Student edition（开发候选）

Windows 本地个人消费记录：只有两个空间——**Capture**（记一笔）和 **Review**（看这个月）。
仅使用 Python、PySide6 与标准库 sqlite3，无网络服务、登录或云同步。
本分支在 v1.1.0 上改进录入、撤销、学习控制与数据保护；尚未发布新版 Windows 包。
界面遵循 `docs/design/` 中的设计规范及 [Student edition 修订](docs/design/Student_Edition_Amendment.md)。[文档入口](docs/README.md)区分长期产品约束、维护规则、当前状态和历史实施记录。

## 当前候选与运行

候选改动和回退：[开发记录](docs/development/STUDENT_EDITION.md)。
实测证据、截图及限制：[验收矩阵](docs/development/STUDENT_VALIDATION.md)。
公开前的剩余工作：[开源准备清单](docs/OPEN_SOURCE_READINESS.md)。许可证未变，本分支不表示已开源。

已有 Python 环境时，安装 `requirements-dev.txt`，然后 `python main.py`。Windows 默认数据目录保持不变。
Linux 只用于开发验证，请显式指定新的合成目录：

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python main.py --data-dir "$PWD/work/my-synthetic-ledger"
```

不要把测试目录当作日常账本。Windows 发行构建仍使用下文的 `build.ps1`，本轮未运行 Windows 构建。

## 既有 v1.1.0 下载与直接运行

从私有仓库 [v1.1.0 Release](https://github.com/Lorentz-Caldfilis/Cashing/releases/tag/v1.1.0)
下载 **Cashing-v1.1.0-windows.zip**，完整解压后双击 **Cashing/Cashing.exe**。
无需安装 Python，无需运行 start.bat，首次启动自动创建空账本。

本项目的正式发行目录：
`D:\Dev\Cashing\release\Cashing-v1.1.0-windows\Cashing\`

正式 EXE：
`D:\Dev\Cashing\release\Cashing-v1.1.0-windows\Cashing\Cashing.exe`

发行包：
`D:\Dev\Cashing\release\Cashing-v1.1.0-windows.zip`

**必须保留整个 Cashing 文件夹，尤其是 _internal。不能只复制 EXE，也不要在 ZIP 预览中直接运行。**
`start.bat` 仅是源码开发辅助脚本；`build` 和 `dist` 是构建目录。
程序自带版本信息 1.1.0，尚未数字签名。

## 日常操作

- **Capture（记一笔）**：启动即进入，金额已获得焦点。输入 `28.5`、Enter、一句说明、Enter，即记录；
  说明可以为空（`28.5` Enter Enter）。时间默认为现在，点击“今天 20:10”可改。
  写入数据库成功后才清空输入；底部短暂出现“已记录 ¥28.50 · 晚饭  撤销”，点“撤销”删除该记录；若没有开始下一笔则恢复原输入，已有下一笔输入时保留它。
  空金额框可按 Ctrl+V 粘贴 `18.5 午饭` 或 `￥１，２８０．５０ 打印资料`，确认后按 Enter 保存；不会覆盖已有说明。
  金额非法只在金额下方提示；保存失败时输入原样保留。Capture 不要求选择类别，类别由软件在 Review 中派生显示。
- **Review（看这个月）**：`‹ 2026年9月 ›` 切换月份（不能进入未来月份，点月份文字回到本月）；
  下方依次是月总额、生活/工具/娱乐三项金额、一个小环形图、按天分组的记录。软件尚未判断类别的金额
  只以极弱的一句“另有 ¥X 尚未分类”出现，总额始终包含它，不需要处理。三类都为 0 时不画环形图，三项金额移到中线上。
- **自动分类**：软件只在证据充分时判断类别（常见说明如“午饭”“地铁”“Steam”），因人而异的（奶茶、咖啡、书……）
  和证据不足的保持未判断。在 Review 里改一次类别，同样说法的其他记录（包括过去的）随之改变；
  一次性的例外（比如生日那顿午饭算娱乐）不会改写其他记录，同一说法纠正两次才会改变原本明确的判断。
  行内“自动 / 自选”直接说明分类来源；未判断行仍显示可点击的“暂未判断”，无需处理也不影响总额。
  选“暂未判断”也会被记住；选“自动判断”移除该条个人标签，让本机重新判断。
  编辑后的通知可撤销，包括分类来源和学习影响；已被再次修改的记录不会被旧撤销覆盖。完全在本地计算，无模型文件、无网络；详见 `docs/development/CLASSIFICATION.md`。
- **切换空间**：点击窗口左右边缘、Alt+← / Alt+→、点击底部“记一笔 / 看账单”，或触控板横向滑动。
  普通 ←/→ 只在文本框内移动光标。
- **原地编辑**：单击某条记录即可修改金额、说明、时间、分类；离开字段即生效，Enter 完成，Esc 放弃，
  点击空白退出；已提交的修改可通过通知撤销。非法输入在该条记录下方提示，并阻止离开，直到改正或按 Esc。
- **删除**：进入编辑的记录右侧有一条细红边，靠近后展开为“删除”，点击立即删除并显示“已删除 … 撤销”；
  选中记录本身（点击记录空白处）后按 Delete 也可删除。没有确认框，只有撤销。
- **搜索**：Review 右上角放大镜或 Ctrl+F，搜索全部历史的说明文字；结果可直接原地编辑；× 或 Esc 退出并回到原月份。
- **更多（⋮）**：打开数据目录、备份账本、关于。备份生成未加密的一致 SQLite 快照，只接受新文件名，不覆盖已有文件。
- **撤销快捷键**：Ctrl+Alt+Z 执行当前通知的撤销；Ctrl+Z 仍是文本编辑。撤销限于当前窗口最近的通知，不跨重启。
- 金额为人民币，范围 ¥0.01～¥999,999,999.99，最多两位小数，数据库存整数分；静态显示统一两位小数并按千分组。
- 时间精确到分钟，范围 1900～9999 年，作为本地墙上时间存储，不自动转换时区。
  说明最多 200 字符；补充平面字符在 Qt 输入框中可能按两个 UTF-16 单元计数。

## 数据、备份与升级

开发模式和打包模式均默认使用：
`%LOCALAPPDATA%\Cashing\ledger.sqlite3`

“⋮ → 关于 Cashing”显示本次实际数据库完整路径，“⋮ → 打开数据目录”直接打开该目录。
与工作目录、安装目录和 PyInstaller 临时目录无关；替换发行目录不会覆盖账单。
不要把真实数据库放进程序目录、Git 或发行包。

数据目录还包含轮转错误日志 `cashing.log`，以及输入停止 350 毫秒后保存的未完成输入 `draft.json`
（草稿不是记录，不参与 Review、统计和搜索，下次启动恢复到 Capture）。
数据库结构、完整性或记录格式无效时会报告错误，**不会删除、清空或自动重建旧账本**。
读库失败显示“无法读取账单”和“—”，不会伪装成零消费。
失败输入保留在页面里，便于重试。短窗口可滚动录入区；长错误详情可滚动与复制，出现时会自动显示。

**从 v1.0.0 升级**：数据库结构升级到 v3（旧类别“饮食”改名为“生活”；类别只保存你自己选过的，
并标明是你选的——v1 的每个类别都是你选的，因此全部保留为你的；软件自己的判断不写入数据库，每次显示时计算；
金额、时间、说明、记录 ID 全部保留）。首次用新版打开旧账本时，会先在同目录生成
`ledger.sqlite3.before-v3.bak`（升级前的完整副本），再在一个事务内完成升级；任何一步失败都会回滚，
旧文件保持原样。升级后的账本不能再用 v1.0.0 打开。

备份：使用“⋮ → 备份账本…”可在运行中生成 SQLite 一致快照；包含全部账单与个人类别标签，不含草稿或错误日志。
选择支持硬链接的本地文件系统（如 NTFS），已有文件名或不支持的文件系统会报错而不覆盖。
也可关闭所有 Cashing 窗口后复制 ledger.sqlite3。
恢复前先保留当前文件的副本，再在关闭软件的状态下恢复备份。
账单与备份都是未加密 SQLite 文件；没有定时自动备份。草稿原子替换能保护旧文件，但不保证账本提交与草稿清除之间的断电一致性。
草稿保存失败会提示；关闭时失败保留窗口，检查磁盘空间或目录权限后重试。

## 源码环境

目标：Windows 10 1809+ / Windows 11，x86-64。
已记录的验证环境为 Windows 11、Python 3.14.7、PySide6/Qt 6.11.2。当前运行依赖只有 PySide6；环形图使用 QPainter，不依赖 Matplotlib。
Windows 10 实机及未装 Python 的干净机器仍需人工验收。

```powershell
cd D:\Dev\Cashing
python -m venv .venv
New-Item -ItemType Directory -Force work | Out-Null
$env:TEMP = "$PWD\work"
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = "$PWD\work\pip-cache"
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe .\main.py
```

仅运行源码安装 requirements.txt（只有 PySide6）即可；测试/打包使用 requirements-dev.txt。
完整已验证依赖版本固定在 requirements-lock.txt。
安装依赖需要联网，装好后的业务功能和发行版不需要联网。
无需激活虚拟环境，也无需改变系统 Python 环境。

## 测试和实际运行验证

```powershell
cd D:\Dev\Cashing
$env:QT_QPA_PLATFORM = "windows"
.\.venv\Scripts\python.exe -m pytest --basetemp .\work\pytest-manual -q
```

**--basetemp 是 pytest 可清理的专用测试目录，绝不能指向真实数据。**
测试默认使用 offscreen；上面的环境变量使 GUI 测试使用原生 Windows 平台。

源码原生 GUI 流程、中文空格路径、重启和缩放验证：
```powershell
.\.venv\Scripts\python.exe .\scripts\verify_release.py --phase source --label manual-source
```

已整理的发行版验证：
```powershell
.\.venv\Scripts\python.exe .\scripts\verify_release.py --phase frozen --install D:\Dev\Cashing\release\Cashing-v1.1.0-windows\Cashing --label manual-frozen
```

验收脚本会在 work 下创建合成记录，操作实际窗口并输出 JSON 与截图。
再次完整执行脚本时请换一个新 --label，避免复用默认路径验证数据。
`--smoke-test` 强制使用 `smoke-ledger.sqlite3`，拒绝默认用户数据目录、含 ledger.sqlite3 的目录和未标记的非空目录。
直接指定 `--data-dir` 只影响本次运行；不得将验收目录当成日常账本。

## 构建与发行

```powershell
cd D:\Dev\Cashing
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
.\.venv\Scripts\python.exe .\scripts\package_release.py
```

build.ps1 使用 PyInstaller onedir，重新生成 build/dist，构建前请关闭应用。
它为自身进程隔离 PATH 和缓存目录，避免收集其他软件不兼容的 DLL，结束后恢复环境。
中文使用 Qt/Windows 系统字体，不下载网络字体；环形图由 QPainter 绘制，不再依赖 Matplotlib。

package_release.py 整理 release 下的正式目录和 ZIP，附带依赖声明、许可证文件、
MANIFEST.sha256 逐文件清单及 ZIP SHA-256。
它拒绝覆盖已有同名发行目录，避免无意替换已经交付的文件。
要再次制作同版本发行包，请先保留旧包，再自行清理已确认的生成目录。

```powershell
Get-FileHash .\release\Cashing-v1.1.0-windows.zip -Algorithm SHA256
```

## 代码结构

- main.py：启动、中文设置、数据路径与错误处理。
- database.py：全部 SQL、事务、schema v3 与 v1/v2→v3 迁移、已有记录检查。
- domain.py：金额校验与格式、类别（含“暂未判断”）、月份运算、按天分组、时间文案。
- ledger.py：UI 无关的记录操作（新增/撤销/编辑/删除/恢复/搜索/月视图）。
- classification.py：派生类别（用户自己的短语投票 → 内置词最长匹配 → 不判断），只用标准库。
- lexicon.py：内置词、中心字、因人而异词与中性词。
- draft.py：原子保存 Capture 草稿（`draft.json`）。
- quick_entry.py：Qt 无关的单笔粘贴解析与严格校验。
- paths.py：数据目录与验收目录隔离。
- ui/：theme（视觉 token）、main_window（双空间、具名导航、边缘、Toast、⋮）、spaces（页面切换）、
  capture_page、review_page、record_row（原地编辑与删除边）、toast。
- docs/design/：设计规范；docs/PRODUCT.md、docs/MAINTENANCE.md：长期产品与工程约束；docs/STATUS.md：注明核对日期的状态快照；docs/development/IMPLEMENTATION_STATUS.md：历史实施记录。
- tests/：业务、SQLite、迁移、路径、Ledger、草稿、GUI（Capture / 切换 / Review / 编辑 / 搜索）。
- scripts/：开发与验收工具——smoke_check.py（`main.py --smoke-test` 调用的 GUI 自动验收）、verify_release.py（原生进程验收）、
  package_release.py（发行包生成）、classification_benchmark.py（分类基准，合成数据、确定性）。
- Cashing.spec、version_info.txt、build.ps1：Windows 构建配置。
- docs/releases/v1.0.0/RELEASE_AUDIT.md：v1.0.0 的历史审计证据和限制。
- 开发缓存、测试账本、日志、发行二进制均被 Git 忽略。

## 验收范围和已知限制

- 当前版本、远端 Release 与本次核对结果见 docs/STATUS.md；v1.0.0 发布审计和 UI v2 实施记录分别见 docs/releases/v1.0.0/RELEASE_AUDIT.md、docs/development/IMPLEMENTATION_STATUS.md。
- 已自动验证窗口交互、源码/EXE 重启、特殊路径和多个缩放比例；这不等同于所有 Windows 机器均已验收。
- Windows 10、无 Python 干净机器、真实中文 IME 输入、跨显示器拖动及物理断网仍需人工验收。
- 仅消费和固定三类（生活、工具、娱乐，可暂未判断），无收入、预算、账户、云同步、导出、复杂报表。
- 自动分类的效果来自合成基准（新用户第 6 个月约 99% 精确、80% 以上覆盖），尚未在真实长期使用中验证；
  内置词面向中国大陆学生消费。设计与评估见 docs/development/CLASSIFICATION.md。
- 月度记录整体加载，未做超大数据集或长期数月运行压力测试。
- 不支持多窗口对同一条记录的并发编辑冲突合并。
- 安装目录可只读，用户数据目录必须可写。
- 第三方依赖授权声明与原始许可证文件随发行包提供，源代码项目未另行授予公开开源许可。

参考：[Qt 平台支持](https://doc.qt.io/qt-6/supported-platforms.html)、
[PyInstaller spec](https://pyinstaller.org/en/stable/spec-files.html)。
