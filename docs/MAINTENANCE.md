# Cashing 维护规范

**状态：** 长期维护。当前版本和验收结果放在 [STATUS.md](STATUS.md)，避免把一次运行的数字当成永久规范。产品判断先看 [PRODUCT.md](PRODUCT.md)及原始设计规范。

## 分层与不变量

| 层 | 责任 |
|---|---|
| `main.py`、`paths.py` | 启动、运行数据目录、隔离验收目录、错误入口 |
| `database.py` | SQLite、schema、校验、事务、迁移和备份；项目唯一 SQL 入口 |
| `ledger.py` | 不依赖 Qt 的记录操作、撤销快照、读取时派生类别 |
| `classification.py`、`lexicon.py` | 本地分类和保守的词汇证据 |
| `domain.py`、`draft.py`、`quick_entry.py` | 金额与时间规则、汇总、独立于账单的原子草稿与单笔粘贴解析 |
| `ui/` | PySide6 界面、视觉 token、动效、两个空间 |

UI 只调用 `Ledger`，不得直接写 SQL。UI 看到的 `record.category` 可能是派生值；写回或恢复前必须从数据库取得已存储的记录，不得把展示记录当成原始行。`category_by_user=1` 表示用户明确选择了某类别，包括 `(NULL, 1)` 的“暂未判断”；`(NULL, 0)` 表示用户未指定。软件自己的类别仅在读取时计算。

金额以整数分验证、存储、汇总；绘制比例时才可使用浮点数。时间是本地墙上时间，精确到分钟，不隐式转换时区。Core 保持离线，运行时依赖尽量少；增加依赖前评估发行体积、许可证、冷启动和可维护性。

## 数据安全与兼容

正式数据默认在 `%LOCALAPPDATA%\Cashing\ledger.sqlite3`，草稿在同目录 `draft.json`，错误日志在 `cashing.log`。构建、安装和测试目录不得承载正式账本。测试只使用新建的 `work/` 目录；`pytest --basetemp` 不得指向用户数据。`--smoke-test` 只能操作隔离目录中的 `smoke-ledger.sqlite3`。

现行 schema v3 接受并迁移 v1/v2。改变 schema 时，先列出旧版本及失败场景，保留金额、时间、说明、ID 和用户类别语义；验证现有结构与数据，先生成完整备份，在单个显式事务内修改并校验，失败回滚。对损坏或未知版本停止并报错，绝不自动重建。新增迁移应有合成旧库、失败回滚、重复打开和备份内容的测试；不读取真实账本做开发测试。

可用“备份账本”生成运行中的一致 SQLite 快照；目标必须是新文件名，文件系统必须支持硬链接发布。手工复制真实账本仍应关闭所有 Cashing 窗口。恢复前另存当前文件。备份与恢复文案必须说明 SQLite 文件未加密，以及升级备份不等于持续自动备份。

## 修改与验证门槛

- 产品或视觉变动：依据文档优先级确认主路径与空间记忆未变。涉及焦点、原地编辑、删除撤销、月份切换和动效时，验证相应 GUI 状态；真实触控板、IME 和显示器观感不能由自动测试代替。
- 分类变动：保持“高精确率，允许不判断”。用 `scripts/classification_benchmark.py` 的合成 DEV 调整，在未参与本轮调整的样本上报告精确率、覆盖率和误差。已有 TEST/FRESH 结果是历史对照；反复据此调参后，它们不再是新的盲测集，必要时应另建留出样本。合成结果不可写成真实长期效果。真实使用中的匿名失败例子应转成回归用例，不能读取正式账本。
- 性能变动：先在可复现的合成大月份上测量，再改 Review 的重建、搜索或缓存；不得为推测的瓶颈破坏数据一致性或编辑行为。
- 发布变动：同步 `main.py`、`version_info.txt`、`scripts/package_release.py`、README 和发行名称。先跑测试，再分别验证源码、冻结 EXE 和解压后的发行包；真实进程、GUI 缩放和重启持久化结果单列。构建只生成隔离产物，不覆盖同名已发布包。

推荐的源码测试命令（PowerShell，在项目根目录）：

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp .\work\pytest-maintenance -q -W error
.\.venv\Scripts\python.exe .\scripts\verify_release.py --phase source --label unique-source-label
```

每次运行 `verify_release.py` 使用新的 `--label`；详见根目录 README。发布时记录源码提交、依赖锁文件、测试命令与结果、发行文件摘要、GitHub tag 和 Release asset 的摘要。旧版本审计留作历史证据，不能覆盖成新版本的验收结论。没有实测的平台和设备须明确列出。

## 文档更新约定

长期原则修改时更新原始 `docs/design/` 规范及本摘要，并解释为什么原判断不再成立。实现或数据行为改变时同步 README、`PRODUCT.md` 或本文中的对应描述；每次发布更新 `STATUS.md` 的日期、提交、远端证据和未验收项。`docs/development/IMPLEMENTATION_STATUS.md` 保留为历史记录，新增进展不再附在其旧“当前阶段”之后。
