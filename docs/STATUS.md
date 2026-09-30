# Cashing 状态快照

## 2026-09-30 开发候选

独立分支 `codex/student-edition-20260930`，基线 `ebd0c8b`，草稿 [PR #2](https://github.com/Lorentz-Caldfilis/Cashing/pull/2)。
未修改 main、未发布新版、未改变许可证。新增原子草稿、单笔粘贴、可逆分类学习、备份和具名 PC 导航。
最终 Linux/offscreen 268 项测试通过；Linux X11 五次独立进程缩放/重启验收通过。
完整证据与明确未测项见 [验收矩阵](development/STUDENT_VALIDATION.md)，回退见 [开发记录](development/STUDENT_EDITION.md)。
本轮未重核历史 Release 资产；下面保留原来的 2026-09-27 发布快照，不作为本分支的发布证据。

---

**核对日期：** 2026-09-27。此页是可更新的快照；不能把它当成长期不变的设计约束。稳定规则见 [PRODUCT.md](PRODUCT.md)和 [MAINTENANCE.md](MAINTENANCE.md)。

## 版本与远端

- 本次文档维护前的源码基线：`08e333b7671a952d52c75f43a8338fe725be68d1`；核对时本地与 GitHub `main` / `HEAD` 一致。后续文档提交会推进 `main`，不改变此处记录的应用源码基线。
- GitHub 仓库：[`Lorentz-Caldfilis/Cashing`](https://github.com/Lorentz-Caldfilis/Cashing)，私有，默认分支 `main`，未归档；核对时无开放 PR。私有仓库页面需要访问权限。
- 最新 Release：[`v1.1.0`](https://github.com/Lorentz-Caldfilis/Cashing/releases/tag/v1.1.0)，已发布、非预发布。`v1.1.0` 注释标签指向上述提交。
- GitHub 发行资产 `Cashing-v1.1.0-windows.zip` 的服务器 SHA-256 与本地 ZIP 相同：`54f28cc138822d586c45a2bea04b84126e1d751dbbba7a594d6f50b40589f0db`。这证明本地 ZIP 与远端资产一致，不证明所有设备上的运行体验。

## 已实现

Windows PC Light 双空间 Capture / Review；金额、说明、时间的快速记录；月度汇总和按天历史；搜索、原地编辑、删除和撤销；独立草稿；仅存用户指定类别、读取时本地派生分类。Python + PySide6 + 标准库 sqlite3，schema v3，PyInstaller onedir 发行。Core 没有运行时网络依赖。

## 本次核对与尚未验证

- 本次执行源码测试：`237 passed`（`-W error`，Windows，隔离的 `work/pytest-maintenance-20260927`）。
- 本次执行 `scripts/verify_release.py`：源码和本地冻结版各 `PASS`，每个阶段启动 5 个原生 GUI 进程；报告分别在 `work/docs-20260927-source/verification.json`、`work/docs-20260927-frozen/verification.json`。冻结版检查还确认默认数据路径重启持久化及安装目录未变化；所有数据位于隔离的 `work/` 验收目录。
- 既有 `v1.1.0` 发行包与远端摘要相同。本次文档维护未重打包、未覆盖已发布资产。
- 分类精确率约 99%、覆盖率约 82–83% 是仓库中确定性**合成**基准的新用户第 6 个月结果，不是实际用户长期效果。
- 真实触控板方向与手感、中文 IME、跨显示器移动、Windows 10、未安装 Python 的干净机器、物理断网和长期大数据量仍需要分别验收。既有自动 GUI 与进程记录见历史实施文件；它们不能替代这些人工/环境验收。

## 维护时更新

修改此页时重新核对 `git status`、本地/远端 `main`、标签解引用、Release 元数据与资产摘要、版本字符串及实际测试输出。只记录本次真正运行过的检查；远端无法访问时标明仅为本地或历史证据。详细操作与数据安全规则见 [MAINTENANCE.md](MAINTENANCE.md)。
