# 参与开发

先阅读 [产品约束](docs/PRODUCT.md)、[维护规范](docs/MAINTENANCE.md)与
[Student edition 设计修订](docs/design/Student_Edition_Amendment.md)。项目采用 MIT；提交贡献表示你有权按同一许可提供该贡献，版权仍属于各自作者。无需转让版权。

1. 从明确的基线创建独立分支；保留他人未提交改动。
2. 使用新建的 `work/` 合成数据目录，不提交账本、草稿、日志或个人失败样例。
3. SQL 仅在 database.py；UI 调用 Ledger；金额使用整数分。
4. 针对改动运行测试，阶段结束运行完整测试；记录真实运行的平台和未测试项目。
5. PR 说明问题、新行为、验证与回退方法。数据迁移必须另行说明兼容、备份与失败回滚。

```bash
.venv/bin/python -m pytest -q -W error --basetemp work/pytest-contribution
.venv/bin/python scripts/verify_desktop.py --platform offscreen --label contribution-unique
```

`--basetemp` 会被 pytest 清理，只能指向专用测试目录。原生 Windows 与发行包验收命令见 README。
不要把 Linux/offscreen 的通过结果写成 Windows 实机通过；不要修改许可证、公开仓库或发布资产，除非所有者明确授权。

## Windows 与候选包

Windows 在仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest -q -W error --basetemp work/pytest-contribution
.\.venv\Scripts\python.exe scripts/verify_release.py --phase source --label contribution-source-01
```

PR 的 Windows Actions 使用精确 head SHA，而非临时合并提交；失败时先检查具体步骤与 JUnit，
不能把上传成功当作测试通过。构建/解压步骤见 [Windows 候选验证](docs/WINDOWS_CANDIDATE.md)。
新增依赖或资源必须更新 [来源记录](docs/THIRD_PARTY.md)；上游授权文本保留原始字节和来源摘要。
Qt 界面变动应附合成截图；原生输入法、触控板等未测项目必须列出。

分类评估的固定 DEV/HOLDOUT 不因结果不好而修改。覆盖率和错误决定分开报告，
新增失败场景加入独立回归集；不要为提高合成分数扩大弱证据推断。
SQLite `with connection` 只管理事务，不关闭连接；测试也必须显式 close 或使用 contextlib.closing。

## 提交前检查

```bash
.venv/bin/python scripts/audit_repository.py --output work/repository-audit.json
```

该工具只扫描本地可达 Git blob 的少量敏感模式，不打印匹配值；不是完整泄漏检测认证。
还需检查当前未跟踪文件、截图和日志，不能依赖 `.gitignore` 保护已经跟踪的文件。
报告故障与体验建议可使用 issue 模板；安全问题先按 SECURITY.md 处理。
