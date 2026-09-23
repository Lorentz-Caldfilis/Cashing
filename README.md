# Cashing v1.0.0

Windows 本地个人消费记录：只有两个空间——**Capture**（记一笔）和 **Review**（看这个月）。
仅使用 Python、PySide6 与标准库 sqlite3，无网络服务、登录或云同步。
界面遵循 `docs/design/` 中冻结的设计规范（PC Light Mode v2）；实现进度见 `docs/development/IMPLEMENTATION_STATUS.md`。

## 下载与直接运行

从私有仓库 [v1.0.0 Release](https://github.com/Lorentz-Caldfilis/Cashing/releases/tag/v1.0.0)
下载 **Cashing-v1.0.0-windows.zip**，完整解压后双击 **Cashing/Cashing.exe**。
无需安装 Python，无需运行 start.bat，首次启动自动创建空账本。

本项目的正式发行目录：
`D:\Dev\Cashing\release\Cashing-v1.0.0-windows\Cashing\`

正式 EXE：
`D:\Dev\Cashing\release\Cashing-v1.0.0-windows\Cashing\Cashing.exe`

发行包：
`D:\Dev\Cashing\release\Cashing-v1.0.0-windows.zip`

**必须保留整个 Cashing 文件夹，尤其是 _internal。不能只复制 EXE，也不要在 ZIP 预览中直接运行。**
`start.bat` 仅是源码开发辅助脚本；`build` 和 `dist` 是构建目录。
程序自带版本信息 1.0.0，尚未数字签名。

## 日常操作

- **Capture（记一笔）**：启动即进入，金额已获得焦点。输入 `28.5`、Enter、一句说明、Enter，即记录；
  说明可以为空（`28.5` Enter Enter）。时间默认为现在，点击“今天 20:10”可改。
  写入数据库成功后才清空输入；底部短暂出现“已记录 ¥28.50 · 晚饭  撤销”，点“撤销”删除该记录并恢复原输入。
  金额非法只在金额下方提示；保存失败时输入原样保留。Capture 不要求选择类别，类别由软件在 Review 中派生显示。
- **Review（看这个月）**：`‹ 2026年9月 ›` 切换月份（不能进入未来月份，点月份文字回到本月）；
  下方依次是月总额、生活/工具/娱乐三项金额、一个小环形图、按天分组的记录。软件尚未判断类别的金额
  只以极弱的一句“另有 ¥X 尚未分类”出现，总额始终包含它，不需要处理。三类都为 0 时不画环形图，三项金额移到中线上。
- **切换空间**：点击窗口左右边缘、Alt+← / Alt+→、点击底部圆点，或触控板横向滑动。
  普通 ←/→ 只在文本框内移动光标。
- **原地编辑**：单击某条记录即可修改金额、说明、时间、分类；离开字段即生效，Enter 完成，Esc 放弃，
  点击空白退出。非法输入在该条记录下方提示，并阻止离开，直到改正或按 Esc。
- **删除**：进入编辑的记录右侧有一条细红边，靠近后展开为“删除”，点击立即删除并显示“已删除 … 撤销”；
  选中记录本身（点击记录空白处）后按 Delete 也可删除。没有确认框，只有撤销。
- **搜索**：Review 右上角放大镜或 Ctrl+F，搜索全部历史的说明文字；结果可直接原地编辑；× 或 Esc 退出并回到原月份。
- **更多（⋮）**：打开数据目录、关于。没有设置页。
- 金额为人民币，范围 ¥0.01～¥999,999,999.99，最多两位小数，数据库存整数分；静态显示统一两位小数并按千分组。
- 时间精确到分钟，范围 1900～9999 年，作为本地墙上时间存储，不自动转换时区。
  说明最多 200 字符；补充平面字符在 Qt 输入框中可能按两个 UTF-16 单元计数。

## 数据、备份与升级

开发模式和打包模式均默认使用：
`%LOCALAPPDATA%\Cashing\ledger.sqlite3`

“⋮ → 关于 Cashing”显示本次实际数据库完整路径，“⋮ → 打开数据目录”直接打开该目录。
与工作目录、安装目录和 PyInstaller 临时目录无关；替换发行目录不会覆盖账单。
不要把真实数据库放进程序目录、Git 或发行包。

数据目录还包含轮转错误日志 `cashing.log`，以及关闭程序时未完成的输入 `draft.json`
（草稿不是记录，不参与 Review、统计和搜索，下次启动恢复到 Capture）。
数据库结构、完整性或记录格式无效时会报告错误，**不会删除、清空或自动重建旧账本**。
读库失败显示“无法读取账单”和“—”，不会伪装成零消费。
失败输入保留在页面里，便于重试。

**从 v1.0.0 升级**：数据库结构从 v1 升级到 v2（类别可为空，旧类别“饮食”改名为“生活”，
金额、时间、说明、记录 ID 全部保留）。首次用新版打开旧账本时，会先在同目录生成
`ledger.sqlite3.before-v2.bak`（升级前的完整副本），再在一个事务内完成升级；任何一步失败都会回滚，
旧文件保持原样。升级后的账本不能再用 v1.0.0 打开。

备份：关闭所有 Cashing 窗口后复制 ledger.sqlite3。
恢复前先保留当前文件的副本，再在关闭软件的状态下恢复备份。
账单是未加密 SQLite 文件，除升级前副本外没有自动备份。

## 源码环境

目标：Windows 10 1809+ / Windows 11，x86-64。
当前实际验证环境为 Windows 11、Python 3.14.7、PySide6/Qt 6.11.2、Matplotlib 3.11.2。
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
.\.venv\Scripts\python.exe .\scripts\verify_release.py --phase frozen --install D:\Dev\Cashing\release\Cashing-v1.0.0-windows\Cashing --label manual-frozen
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
Get-FileHash .\release\Cashing-v1.0.0-windows.zip -Algorithm SHA256
```

## 代码结构

- main.py：启动、中文设置、数据路径与错误处理。
- database.py：全部 SQL、事务、schema v2 与 v1→v2 迁移、已有记录检查。
- domain.py：金额校验与格式、类别（含“暂未判断”）、月份运算、按天分组、时间文案。
- ledger.py：UI 无关的记录操作（新增/撤销/编辑/删除/恢复/搜索/月视图）。
- classification.py：派生类别的最小实现（相同说明沿用用户最近的类别，其余保持未判断）。
- draft.py：Capture 草稿（`draft.json`）。
- paths.py：数据目录与验收目录隔离。
- ui/：theme（视觉 token）、main_window（双空间、圆点、边缘、Toast、⋮）、spaces（页面切换）、
  capture_page、review_page、record_row（原地编辑与删除边）、toast。
- docs/design/：冻结的设计规范。docs/development/IMPLEMENTATION_STATUS.md：本轮实现记录。
- tests/：业务、SQLite、迁移、路径、Ledger、草稿、GUI（Capture / 切换 / Review / 编辑 / 搜索）。
- scripts/：发行包生成及原生进程验收。
- Cashing.spec、version_info.txt、build.ps1：Windows 构建配置。
- docs/releases/v1.0.0/RELEASE_AUDIT.md：本轮发现、修复、验证证据和限制。
- 开发缓存、测试账本、日志、发行二进制均被 Git 忽略。

## 验收范围和已知限制

- v1.0.0 发布审计见 docs/releases/v1.0.0/RELEASE_AUDIT.md；UI v2 的测试与验证记录见 docs/development/IMPLEMENTATION_STATUS.md。
- 已自动验证窗口交互、源码/EXE 重启、特殊路径和多个缩放比例；这不等同于所有 Windows 机器均已验收。
- Windows 10、无 Python 干净机器、真实中文 IME 输入、跨显示器拖动及物理断网仍需人工验收。
- 仅消费和固定三类（生活、工具、娱乐，可暂未判断），无收入、预算、账户、云同步、导出、复杂报表。
- 自动分类目前只沿用“相同说明”的历史类别；正式的自适应分类规范尚未冻结。
- 月度记录整体加载，未做超大数据集或长期数月运行压力测试。
- 不支持多窗口对同一条记录的并发编辑冲突合并。
- 安装目录可只读，用户数据目录必须可写。
- 第三方依赖授权声明与原始许可证文件随发行包提供，源代码项目未另行授予公开开源许可。

参考：[Qt 平台支持](https://doc.qt.io/qt-6/supported-platforms.html)、
[PyInstaller spec](https://pyinstaller.org/en/stable/spec-files.html)。
