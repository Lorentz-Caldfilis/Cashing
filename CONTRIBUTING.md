# 参与开发

先阅读 [产品约束](docs/PRODUCT.md)、[维护规范](docs/MAINTENANCE.md)与
[Student edition 设计修订](docs/design/Student_Edition_Amendment.md)。项目尚未授予公开开源许可。

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
