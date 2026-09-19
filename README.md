# Cashing v1.0.0

Windows 本地个人消费记账：记录消费 → 本地保存 → 按月查看 → 分类核算 → 饼图展示。
仅使用 Python、PySide6、标准库 sqlite3 与 Matplotlib，无网络服务、登录或云同步。

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

- **记账**：填写金额、消费时间、类别和可选说明，点击“保存消费”。
  保存成功后页面内反馈，金额与说明清空，时间重置为当前时间，类别保留。
  在金额或说明框按 Enter 也可保存，焦点回到金额框。
- **查看账单**：进入时显示本月；左右箭头逐月切换，“本月”返回当前月份。
  三类金额、总金额和环形饼图同步刷新；空月份显示零金额和“本月暂无消费记录”。
- **编辑**：双击记录，或选中后点击“编辑”，或右键选择“编辑”。
  修改时间跨月后，记录会移到对应月份。
- **删除**：选中后点击“删除”或右键删除；只确认一次，默认选择取消。
- **明细**：按消费时间倒序，同时间按 ID 倒序。选中后可在下方纯文本框完整查看、滚动和复制说明。
  拖动列宽或缩放窗口后自动重新计算行高；小屏或大缩放时可滚动页面。
- 类别固定为饮食、工具、娱乐。金额为人民币，范围 ¥0.01～¥999999999.99，
  最多两位小数，数据库存整数分。币种符号已经显示在输入框旁。
- 时间精确到分钟，范围 1900～9999 年，作为本地墙上时间存储，不自动转换时区。
  说明最多 200 字符；补充平面字符在 Qt 输入框中可能按两个 UTF-16 单元计数。

## 数据、备份与升级

开发模式和打包模式均默认使用：
`%LOCALAPPDATA%\Cashing\ledger.sqlite3`

程序底部显示本次实际数据库完整路径。
与工作目录、安装目录和 PyInstaller 临时目录无关；替换发行目录不会覆盖账单。
不要把真实数据库放进程序目录、Git 或发行包。

数据目录还包含轮转错误日志 `cashing.log` 和 `cache/matplotlib` 绘图缓存。
数据库结构、完整性或记录格式无效时会报告错误，**不会删除、清空或自动重建旧账本**。
读库失败显示“读取失败”和“—”，不会伪装成零消费。
失败输入保留在表单里，便于重试。

备份：关闭所有 Cashing 窗口后复制 ledger.sqlite3。
恢复前先保留当前文件的副本，再在关闭软件的状态下恢复备份。
账单是未加密 SQLite 文件，v1.0 没有自动备份。

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

仅运行源码安装 requirements.txt 即可；测试/打包使用 requirements-dev.txt。
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
仅打包 QtAgg 后端及所需运行库；中文使用 Qt/Windows 字体，不下载网络字体。
已有 Qt/Matplotlib 数据与平台插件通过实际 EXE 启动核验。

package_release.py 整理 release 下的正式目录和 ZIP，附带依赖声明、许可证文件、
MANIFEST.sha256 逐文件清单及 ZIP SHA-256。
它拒绝覆盖已有同名发行目录，避免无意替换已经交付的文件。
要再次制作同版本发行包，请先保留旧包，再自行清理已确认的生成目录。

```powershell
Get-FileHash .\release\Cashing-v1.0.0-windows.zip -Algorithm SHA256
```

## 代码结构

- main.py：启动、中文设置、数据路径与错误处理。
- database.py：全部 SQL、事务、数据库与已有记录检查。
- domain.py：金额校验、整数分格式、月份运算和分类合计。
- paths.py：数据、绘图缓存与验收目录隔离。
- ui/：主窗口、共用表单、记账、月度明细和编辑对话框。
- tests/：业务、SQLite、路径、GUI 及独立审计回归。
- scripts/：发行包生成及原生进程验收。
- Cashing.spec、version_info.txt、build.ps1：Windows 构建配置。
- RELEASE_AUDIT.md：本轮发现、修复、验证证据和限制。
- 开发缓存、测试账本、日志、发行二进制均被 Git 忽略。

## 验收范围和已知限制

- 本轮单元和 GUI 自动测试为 100 项；详细结果及中间失败记录见 RELEASE_AUDIT.md。
- 已自动验证窗口交互、源码/EXE 重启、特殊路径和多个缩放比例；这不等同于所有 Windows 机器均已验收。
- Windows 10、无 Python 干净机器、真实中文 IME 输入、跨显示器拖动及物理断网仍需人工验收。
- 仅消费和固定三类，无收入、预算、账户、云同步、导出、复杂报表。
- 月度百分比保留一位小数，显示值之和可能因舍入不恰好为 100%；金额合计始终使用整数分。
- 月度记录整体加载，未做超大数据集或长期数月运行压力测试。
- 不支持多窗口对同一条记录的并发编辑冲突合并。
- 安装目录可只读，用户数据目录必须可写。
- 第三方依赖授权声明与原始许可证文件随发行包提供，源代码项目未另行授予公开开源许可。

参考：[Qt 平台支持](https://doc.qt.io/qt-6/supported-platforms.html)、
[Matplotlib Qt 嵌入](https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html)、
[PyInstaller spec](https://pyinstaller.org/en/stable/spec-files.html)。
