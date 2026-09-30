# Windows 候选构建与验收

在仓库根目录使用 Windows PowerShell，安装 README 指定依赖。构建及打包前提交源码修改。
不创建 Release、不上传到发行频道、不改版本或许可。候选 CI 使用 Windows Server 2022 x64，
这与人工 Windows 10/11 设备验收不同。

```powershell
.\.venv\Scripts\python.exe -m pytest -q -W error --basetemp work/pytest-candidate
.\.venv\Scripts\python.exe scripts/verify_release.py --phase source --label candidate-source-01
./build.ps1
.\.venv\Scripts\python.exe scripts/package_release.py
$commit = git rev-parse HEAD
$name = "Cashing-candidate-$($commit.Substring(0,12))-windows"
Get-FileHash "release/$name.zip" -Algorithm SHA256
Expand-Archive -LiteralPath "release/$name.zip" -DestinationPath "work/extracted-$name"
.\.venv\Scripts\python.exe scripts/verify_release.py --phase frozen --install "work/extracted-$name/Cashing" --label candidate-extracted-01
```

将 Get-FileHash 结果与同目录 `.zip.sha256` 对比，并核对包内 BUILD_INFO.json 的完整源码 SHA。
每次完整验收使用新的 label 和解压目录；pytest 的 basetemp 只能指向专用测试目录。

`verify_release.py` 对源码/解压程序执行合成 GUI 流程，包含首次启动、重启持久化、中文空格路径、
100/125/150/200% 缩放。解压程序另验证独立 LOCALAPPDATA 默认路径与两次正常启动，
并比较运行前后 manifest，防止程序把账单写进安装目录。子进程 PATH 不含 Python 开发目录；
runner 本身仍有 Python，因此不能声称“未装 Python 的干净电脑”已测。

PR workflow checkout 精确 head SHA，依赖从 requirements-lock.txt 安装；保存源码 SHA、pip freeze、
JUnit、合成 GUI JSON/截图/日志及候选 ZIP/摘要，保留 14 天。失败运行仍保留已有诊断产物，
必须检查 run conclusion 和步骤状态，不能把“有 artifact”当作通过。

分类固定语料报告与 Windows 证据是两类独立指标；当前平台词保持保守未知。
人工验收还需中文 IME 组合输入、真实触控板、跨屏/DPI、物理断网、低权限用户与目标 Windows 版本。
公开再分发前按 THIRD_PARTY.md 和 OPEN_SOURCE_READINESS.md 完成许可及安全审查。
