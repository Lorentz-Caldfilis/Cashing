# Cashing 开发指南

适用于 **1.2.0**。开始前阅读 [产品设计原则](../PRODUCT.md)和 [维护规范](../MAINTENANCE.md)。

## 代码分层

| 位置 | 职责 |
| --- | --- |
| `main.py`、`paths.py` | 启动、版本、数据目录和错误入口 |
| `database.py` | 唯一 SQL 入口：校验、事务、schema v3、迁移与备份 |
| `ledger.py` | 记录操作、撤销、月视图和读取时分类 |
| `classification.py`、`classification_evidence.py`、`lexicon.py` | 本地分类、用途证据与词汇规则 |
| `domain.py`、`draft.py`、`quick_entry.py` | 整数分金额、时间、原子草稿及单笔粘贴解析 |
| `ui/` | PySide6 两个空间、记录行、系统主题和动效 |
| `assets/` | 应用图标、原图及资源来源 |
| `tests/`、`scripts/` | 回归、合成评估、进程验证与打包工具 |
| `third_party/` | 打包必需的上游授权原文、对应源码清单及摘要 |

调用方向为 `ui → Ledger → Database`。金额存整数分，时间为本地分钟精度。
数据库仅保存事实和用户明确的类别；展示时派生的类别不得写回为个人标签。
默认账本在 `%LOCALAPPDATA%\Cashing`，开发只能使用新建的 `work/` 隔离目录。

## 安装与运行

已验证的 Windows CI 环境为 Python 3.14.7 x64；在根目录执行 PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
$dataDir = Join-Path (Get-Location) 'work\manual-dev-unique'
.\.venv\Scripts\python.exe main.py --data-dir $dataDir
```

`requirements.txt` 仅为运行依赖；`requirements-dev.txt` 增加开发工具；`requirements-lock.txt` 固定构建环境。
隔离目录一旦使用就属于该开发会话，不得拿它替代日常账本。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q -W error --basetemp work/pytest-dev-unique
.\.venv\Scripts\python.exe scripts/verify_release.py --phase source --label dev-source-unique
```

每次使用新的 label。pytest 会清理 basetemp，必须指向专用测试目录。
原生 GUI 验证串行运行，避免抢占焦点；报告在 `work/<label>/verification.json`。
完整进程检查包含五次启动、缩放、重启和主题变化，不能代替人工输入法或不同设备验收。
无显示的开发环境可用 `scripts/verify_desktop.py --platform offscreen --label unique-label`，
但不能据此宣称 Windows 实机通过。分类修改另按 [分类设计](CLASSIFICATION.md)验证。

## Windows 打包

发行形式是 PyInstaller onedir 便携版，`Cashing.exe` 与 `_internal` 必须一起保留。
构建前提交需要打包的源码修改。构建会重建 `build/` 与 `dist/`，它们不应承载账本或交付副本。

```powershell
./build.ps1
.\.venv\Scripts\python.exe scripts/fetch_sources.py
.\.venv\Scripts\python.exe scripts/package_release.py
$commit = (git rev-parse HEAD).Trim()
$name = "Cashing-candidate-$($commit.Substring(0,12))-windows"
Expand-Archive -LiteralPath "release/$name.zip" -DestinationPath "work/extracted-$name"
.\.venv\Scripts\python.exe scripts/verify_release.py --phase frozen --install "work/extracted-$name/Cashing" --label dev-extracted-unique
Get-FileHash "release/$name.zip" -Algorithm SHA256
```

打包要求 tracked 文件干净、构建来源与运行文件一致，拒绝覆盖已有目录/ZIP/摘要及携带私人资料。
包中必须保留应用许可、第三方原文、对应源码和替换说明，详见 [第三方依赖](../THIRD_PARTY.md)。
PR 的 Windows CI 在精确 head commit 上测试、构建、验证解压包，保留 artifact 14 天，不自动创建 Release。
进一步的进程/清单检查见 [Windows 构建验证](../WINDOWS_CANDIDATE.md)。

## 维护约束

- 草稿和账本是不同文件，不保证跨文件的断电事务。只有数据库写入成功才清空输入。
- schema v3 接受 v1/v2，迁移前备份；无效或未知账本应停止，不自动重建。
- `ui/theme.py` 合并系统方案/调色板通知，更新应用与局部样式；图标和图表绘制时取当前 token。
  切换不重建页面、不查询账本，保留输入、编辑、选区和撤销。主题覆盖只用于隔离烟测。
- 图片背景已移除，旧私人图片不读取、不改写、不自动删除；忽略及打包拒绝检查仍保留。
- 普通源码/测试/构建工具是可维护软件的一部分。阶段报告、原始测试输出和历史截图放在本机 `work/` 或 CI，
  当前文档只记录长期约束、操作路径和当前发行身份；旧资料在 Git 历史中可追溯。
- 不自动提交、推送、更新标签或发布；需要所有者明确授权。仓库整理不改 1.2.0 二进制或其源码标签。
