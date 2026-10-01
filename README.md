# Cashing · PC Student edition

安静的本地消费记录工具：**记一笔，看这个月**。面向学生，也适合只想快速记账的人。
无需账号，没有遥测、云同步或联网分类。账单和个性化分类学习保存在自己的电脑。

当前版本 **1.2.0**，包含 Student edition 改进、可选用途和新图标，使用固定浅色界面；发行验证见 [状态快照](docs/STATUS.md)。
采用 [MIT 许可证](LICENSE)，版权所有 © 2026 Lorentz-Caldfilis。允许免费使用、修改、再分发及商用，须保留版权和许可声明；第三方组件各自保留原许可。

## 开始使用

从 [1.2.0 预发行](https://github.com/Lorentz-Caldfilis/Cashing/releases/tag/v1.2.0)取得 Windows ZIP，完整解压后双击 `Cashing/Cashing.exe`，保留整个文件夹。仓库私有期间需要访问权限；源码也可按下文自行构建。
无需安装 Python。候选未数字签名，请核对可信来源和 SHA-256，不要关闭系统安全功能。
旧 v1.0.0 / v1.1.0 二进制已归档为私有草稿；请使用 1.2.0 或从当前 main 构建。

输入 `18.5` → Enter → `午饭` → Enter，即记下一笔。也可在空金额框粘贴 `18.5 午饭`，确认后保存。
时间下方可选生活、工具、娱乐，再次点击取消；未选时沿用自动判断。
点击“看账单”，点击记录即可纠错；“自动 / 自选”说明分类来源，底部通知可撤销。
尚未判断的类别无需处理，不影响总额；明确纠正会影响本机之后的分类。

完整的[使用指南](docs/USER_GUIDE.md)包括第一次记账、纠错学习、键盘操作、备份恢复和卸载。
Windows 默认数据在 `%LOCALAPPDATA%\Cashing`，也可从“⋮ → 打开数据目录”查看。
备份未加密；软件没有定时备份。不要提交或上传个人账本、草稿和日志。

## 从源码运行

在仓库根目录执行。运行只需 `requirements.txt`；开发与构建使用锁定的完整依赖。
安装依赖需要联网，安装完成后的业务功能不需要联网。

Windows PowerShell（CI 使用 Python 3.14.7 x64）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe main.py
```

Linux 仅作开发验证，使用新的合成数据目录：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python main.py --data-dir "$PWD/work/my-synthetic-ledger"
```

不需要激活虚拟环境。`--data-dir` 只影响本次运行，不要把测试目录当日常账本。

## 测试与构建

Windows：

```powershell
.\.venv\Scripts\python.exe -m pytest -q -W error --basetemp work/pytest-manual
.\.venv\Scripts\python.exe scripts/verify_release.py --phase source --label manual-source-01
./build.ps1
.\.venv\Scripts\python.exe scripts/fetch_sources.py
.\.venv\Scripts\python.exe scripts/package_release.py
```

打包前提交源码修改；默认包名包含精确 commit 前 12 位，不沿用正式发行名。
脚本拒绝覆盖已有目录、ZIP 或摘要，拒绝携带数据库、草稿、日志和常见私密配置。
包内包含 `LICENSE`、`BUILD_INFO.json`、依赖清单、许可证来源、Qt/PySide 对应源码归档、逐文件 SHA-256 和独立使用指南。动态库替换见 [说明](docs/LIBRARY_REPLACEMENT.md)。
详细解压验收步骤见 [Windows 候选验证](docs/WINDOWS_CANDIDATE.md)。

Linux 定向开发验证：

```bash
.venv/bin/python -m pytest -q -W error --basetemp work/pytest-manual
.venv/bin/python scripts/verify_desktop.py --platform offscreen --label manual-linux-01
```

`--basetemp` 会被 pytest 清理，只能指向专用测试目录。验收脚本每次使用新的 label。
Windows CI 在 PR 的精确 head commit 上测试、构建并验证解压包，产物保存 14 天，不创建 Release。
源码测试、实际 GUI 进程、冻结包和人工设备验收分开报告，不能互相替代。

## 当前限制与证据

只支持人民币消费和生活/工具/娱乐三类，可暂未判断；没有收入、预算、账户或报表导出。
分类是保守的本地短语规则，合成数据表现不等于真实长期使用效果。
平台词安全回退后的固定学生语料：DEV 明确用途覆盖 8/12，holdout 1/6，两组错误决定均 0；
完整指标和 10 条学习/撤回场景见[第三阶段记录](docs/development/STUDENT_PHASE3.md)。

真实中文 IME、触控板、跨屏、无 Python 的个人电脑和物理断网仍需人工验收。
目前不承诺多窗口冲突合并，也没有超大账本长期压力测试。

- [阶段验收与截图](docs/development/STUDENT_PHASE2.md)、[第三阶段 Windows/打包记录](docs/development/STUDENT_PHASE3.md)
- [贡献指南](CONTRIBUTING.md)、[安全反馈](SECURITY.md)、[开源准备清单](docs/OPEN_SOURCE_READINESS.md)
- [产品约束](docs/PRODUCT.md)、[维护规则与代码分层](docs/MAINTENANCE.md)、[设计修订和回退](docs/design/Student_Edition_Amendment.md)
- [第三方依赖与资源来源](docs/THIRD_PARTY.md)、[文档入口](docs/README.md)
