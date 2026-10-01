# Cashing 开发指南

**适用范围：** 1.2.0，更新日期 2026-10-01。运行入口、实际源码提交和验证范围见 [状态快照](../STATUS.md)。设计取舍先看 [产品约束](../PRODUCT.md)及 [Student edition 修订](../design/Student_Edition_Amendment.md)。

## 代码与数据边界

| 位置 | 职责 |
|---|---|
| `main.py`、`paths.py` | Qt 启动、版本、数据目录、隔离验收目录和启动错误 |
| `database.py` | 唯一 SQL 入口；schema v3、行校验、事务、v1/v2 迁移、升级前备份与一致账本快照 |
| `ledger.py` | 不依赖 Qt 的增删改查、撤销快照、月视图及读取时类别解释 |
| `classification.py`、`classification_evidence.py`、`lexicon.py` | 本地派生分类、词汇证据、用途组合与未知片段处理；最新实现和评估见 [第四阶段记录](STUDENT_PHASE4.md)，旧算法基准见 [分类文档](CLASSIFICATION.md) |
| `domain.py`、`draft.py` | 整数分金额与时间规则、汇总、独立的 Capture 草稿 |
| `quick_entry.py` | 校验单笔人民币金额及说明粘贴，只解析待确认输入，不写账本 |
| `ui/` | PySide6 的 Capture、Review、记录行、导航、主题及动效 |
| `ui/background.py`、`assets/` | 本地背景原子复制、两页共用阅读层及窗口/EXE 图标；不写 SQL |
| `tests/`、`scripts/` | 单元/GUI 测试、原生进程验收、打包及合成分类基准 |

调用方向为 `ui → Ledger → Database`；界面不能直接写 SQL。数据库仅持久化消费事实和用户明确选择的类别。`category_by_user=0` 时类别从说明文字派生；`(category=NULL, category_by_user=1)` 表示用户明确选择“暂未判断”。不能把 UI 展示的派生类别当作已存储类别写回。金额以整数分存储和汇总，时间为本地分钟精度，不隐式转换时区。

默认正式数据目录为 `%LOCALAPPDATA%\Cashing`：`ledger.sqlite3` 是账本，`draft.json` 是未提交输入，`cashing.log` 是轮转错误日志。程序目录、构建目录与账本目录相互独立。`--data-dir` 只供隔离验证；`--smoke-test` 还要求目录为空或带专用标记，并使用 `smoke-ledger.sqlite3`。不得对真实账本执行自动测试、迁移试验或清理。

## 本地开发

在仓库根目录的 PowerShell 中运行；项目已有 `.venv` 时可跳过创建步骤。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe .\main.py
```

`requirements.txt` 是运行依赖；`requirements-dev.txt` 增加 pytest、pytest-qt 和 PyInstaller；`requirements-lock.txt` 记录本轮已验证的完整依赖版本。源码直接启动时默认会打开正式数据目录；开发交互应显式传入一个全新的 `work/` 下绝对路径，例如：

```powershell
$dataDir = Join-Path (Get-Location) 'work\manual-dev-01'
.\.venv\Scripts\python.exe .\main.py --data-dir $dataDir
```

该目录一旦写入记录就属于该次开发会话，不要把它与日常账本混用。更换会话时改用新目录。

## 修改与验证

普通修改先运行相关测试；涉及持久化、版本或发行时运行完整测试，并使用新的 `--label` 做原生 GUI 进程验证。`--basetemp` 指向 pytest 可清理的专用 `work/` 子目录，绝不指向正式数据。

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp .\work\pytest-dev-unique -q -W error
.\.venv\Scripts\python.exe .\scripts\verify_release.py --phase source --label dev-source-unique
```

`verify_release.py` 每阶段运行 5 个原生 Windows GUI 进程，覆盖中文空格路径、重启持久化及多个缩放比例。它的冻结版检查还验证逐文件清单、隔离默认数据路径和安装目录不变。检查报告位于 `work/<label>/verification.json`；标签目录不得复用。自动进程检查不能替代真实触控板、中文输入法或不同设备的人工验收。分类修改另按 [分类文档](CLASSIFICATION.md) 的合成基准与局限执行；数据库迁移另按 [维护规范](../MAINTENANCE.md) 验证备份、回滚和旧数据语义。

## 构建与本地发行

当前发行形式是 **PyInstaller onedir 便携版**，不是单文件 EXE 或安装器。日常入口是发行目录内的 `Cashing.exe`，旁边的 `_internal` 必须保留。构建前关闭正在运行的 Cashing；`build.ps1` 会重建 `build/` 和 `dist/`，它们不是交付目录。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
.\.venv\Scripts\python.exe .\scripts\fetch_sources.py
.\.venv\Scripts\python.exe .\scripts\package_release.py
.\.venv\Scripts\python.exe .\scripts\verify_release.py --phase frozen --install .\release\Cashing-candidate-90b18df8f497-windows\Cashing --label dev-frozen-unique
Get-FileHash .\release\Cashing-candidate-90b18df8f497-windows.zip -Algorithm SHA256
```

`package_release.py` 默认按精确提交命名候选，要求 tracked 文件干净且构建来源一致，拒绝覆盖同名产物。后续提交对应的目录名应根据新提交更新。正式版本变更仍需同步应用与 Windows 版本资源、README 和发行资料；不要替换同名已交付包。候选流程见 [Windows 候选构建](../WINDOWS_CANDIDATE.md)。保留源码、发行目录、ZIP 解压副本的独立结果，并记录摘要与失败。Git 忽略 `release/`、`build/`、`dist/` 和 `work/`。

本地构建不等于 GitHub 发布。推送、标签、Release 页面与服务器资产摘要须在实际操作并核对后记录；当前开发候选与正式 Release 的区别见 [状态快照](../STATUS.md)。

## 当前边界

- Capture 新增可选用途：不选时自动判断，明确选择写入个人标签。草稿、撤销和下一笔保护均包含用途，不更改数据库 schema。
- 背景规范化为数据目录 `appearance-background.png`，QSaveFile 原子替换，导入失败保留旧图，读取失败使用默认。图片不随账本备份；`BackgroundCanvas` 负责裁切与阅读层，页面本身不复制背景。
- EXE 使用多尺寸 ICO，运行图标通过 `__file__` 相对 assets 取得；PyInstaller spec 只带运行资源，不带生成原图/提示词。包内 MIT、第三方授权与对应源码归档缺一不可。

- schema v3 可迁移 v1/v2；迁移前的完整副本是 `ledger.sqlite3.before-v3.bak`。无法识别或损坏的账本应停止并报告，不得自动清空重建。
- 当前有菜单触发的本地一致账本备份，没有定时备份、云同步或账本加密。手工复制正式数据库前应退出程序；恢复前先另存现有文件，具体步骤见使用指南。
- Windows 10、未装 Python 的干净机器、真实中文输入法、触控板方向、跨显示器和长期大账本仍缺少本轮人工验收。不要把合成分类精度或自动 GUI 结果写成真实长期使用效果。
