# 参与 Cashing

欢迎提交 bug、体验建议和 Pull Request。项目采用 MIT；贡献者须有权按同一许可提供贡献，
各自保留其贡献的版权。请先阅读 [产品设计原则](docs/PRODUCT.md)和 [开发指南](docs/development/DEVELOPER_GUIDE.md)。

## 报告问题

请说明版本、系统、操作步骤、预期与实际结果，用虚构的消费记录复现。
不要上传个人账本、备份、私人截图或完整日志。安全问题按 [安全说明](SECURITY.md)私密报告。
分类不准确时，给出匿名说明、期望用途及当前结果即可。

## 提交修改

1. 从现行 main 创建分支，每次 PR 聚焦一个问题。
2. 用新的 `work/` 合成数据目录开发，不操作个人账本。
3. UI 调用 Ledger，SQL 仅在 database.py；金额计算使用整数分。
4. 针对修改运行测试，说明真实验证的平台与未测范围。
5. PR 写清问题、行为变化、验证及回退方法；迁移另说明兼容、备份和失败回滚。

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest -q -W error --basetemp work/pytest-contribution-unique
.\.venv\Scripts\python.exe scripts/verify_release.py --phase source --label contribution-source-unique
```

pytest 会清理 basetemp，只能指向专用测试目录；每次 GUI 验证使用新 label 并串行运行。
Linux/offscreen 测试不能写成 Windows 实机验证。构建及发行检查见 [Windows 构建验证](docs/WINDOWS_CANDIDATE.md)。

数据库修改须遵循 [维护规范](docs/MAINTENANCE.md)；分类修改遵循 [分类设计](docs/development/CLASSIFICATION.md)，
不得为了提高分数修改固定语料或将合成结果声称为真实准确率。
新增依赖或资源须更新 [来源记录](docs/THIRD_PARTY.md)，保留上游许可原文。
产品或操作路径改变时局部更新现行文档，不把阶段日志、完整测试输出及旧截图提交为产品说明。

提交前审查 diff 和隐私文件，可使用 `python scripts/audit_repository.py --output work/repository-audit.json` 辅助扫描；
它只检查少量可达 Git blob 的敏感模式，不是完整泄漏检测。不要自动修改许可、公开仓库或更新发布资产。
