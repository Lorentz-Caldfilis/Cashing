# 第三阶段：可构建、可安装与资料准备

起点 `4e30078`。继续同一 feature 分支 / PR #2；不改 main、许可证、权限或密钥，不发布 Release。
范围：Windows CI 构建及独立解压验收、打包安全、依赖/资源来源、资料审计、初学者指南和 issue 模板。
Windows runner 结果只能证明该 runner 的自动验收，不能替代真实 IME、触控板、跨屏或干净用户设备。

## 优先审查修复：回退平台词中性化

实际复现：`京东 苹果手机`、`淘宝 面具`、`拼多多 汤勺`、`网购 粉底`、`京东 苹果配件`
均被错误决定为生活。原因是弱子串/中心字得到证据，而未识别片段被跳过；不能只补一个商品词。
保守恢复四个平台词的歧义屏障，撤回 `2eac0de` 的词表调整；其固定测试、证据仍保留为历史记录。

不修改冻结 DEV/HOLDOUT：明确用途覆盖回到 DEV 8/12、HOLDOUT 1/6，错误决定均 0；
该覆盖回退是有意接受的安全代价。新增独立的品牌/弱子串/多义词回归集，9 条均保持未判断。
用户明确纠正的完整商品说明仍可学习；10 条学习/撤回检查通过。分类相关 44 项测试通过。
报告：[安全回退后的固定语料](evidence/phase3-20260930/classification-safe.json)。
回退本修复会重引错误，不建议；未来必须先建立完整片段/未知片段证据模型，再重新评估覆盖。

## 环境恢复与 Windows 验证入口

17:50 UTC 恢复后确认原工作区及 Python 环境可读，工作区干净；`7fda6b5` 已在远端 feature 分支，
远端 main 仍为 `ebd0c8b`。没有未保存改动；不把断开期间视为新增测试证据。

新增 `.github/workflows/windows-candidate.yml`：PR 精确 head SHA、Windows Server 2022、
Python 3.14.7、锁定依赖、完整测试、源码真实 Qt 进程、PyInstaller 构建、ZIP 解压后真实进程验证。
Actions 引用完整提交哈希，凭据不保留到 checkout，仅申请读取 contents；保留 14 天的候选包与合成验收证据。
无 tag/Release/部署步骤，不更改仓库设置。YAML 已在 Linux 解析；远端结果需另行记录，不能预判成功。
现有打包许可收集仍需完善，因此 CI 产物仅用于审查验收，不代表可公开再分发。
回退：revert 本次 workflow 提交即可移除自动检查，不影响账本或 schema。

首个 Windows run [36754597243](https://github.com/Lorentz-Caldfilis/Cashing/actions/runs/36754597243)
对 `dcb7107` 实际运行：279 passed / 2 failed，尚未执行构建。
发现 Windows 对只读文件描述符 fsync 报错，改为以 r+b 打开已关闭的临时快照再同步；
未改变拒绝覆盖或失败清理语义。另关闭测试中的两次 SQLite 连接，兼容 Python 3.14 资源警告检查。
新增 flush 失败不发布、不改原账本回归；Linux 定向 6 项通过。Windows 结果等待后续 run。
回退：revert 本次提交会恢复 Windows 备份失败，因此仅用于定位，不建议用于候选。

Windows 修复验证：[run 36754896519](https://github.com/Lorentz-Caldfilis/Cashing/actions/runs/36754896519)
精确源码 `36f04b1809b9ef01bb2f4f26e3b8fce02c1e95cd`，282 tests passed / 18.34s；
源码 5 次 GUI、解压 EXE 5 次 GUI、默认数据目录两次启动和安装 manifest 不变检查通过。
候选 ZIP SHA-256 `733dfaaafcd71705518ca16d48388d4e3fc82092172d8c3313b1adf923cd2006`。
此运行仍是旧打包脚本，不覆盖下一批许可证与打包安全改动。

## 打包安全与可核对来源

下一批打包器改为 commit 命名、包内 BUILD_INFO、完整文件摘要及独立使用指南。
拒绝已有目录/ZIP/摘要、数据库 journal/WAL、草稿、日志、常见凭据文件与链接；
暂存完成后不覆盖发布，失败清理本次输出，保留其他包。DLL 名从构建 Python 版本计算。
许可证从实际 distribution 和精确 Qt/PySide6 v6.11.2 上游收集；134 份文本/attribution
及其来源摘要保存在 third_party。缺少 Python 或 PyInstaller 授权文本时打包失败。
这不改变项目许可，不等于完成公开再分发义务，详见 THIRD_PARTY.md。
Linux 定向打包/备份回归 21 项通过；Windows 新包验收待运行。
回退：revert 本批提交恢复旧打包入口，不修改用户数据；旧候选包不要据此公开发行。

`debe879` 的 Windows run 36755691446 已完成全部步骤，证明新打包器及上游许可证收集可在 runner 执行。
后续补强：构建时保存 BUILD_SOURCE.json，打包拒绝旧 commit 或脏源码构建产物，避免把旧 dist 标作新 HEAD；
解压验收拒绝新增文件、篡改、路径越界与重复 manifest 项，并拒绝复用验收目录。
打包针对性回归 21 项通过；恢复原仓库换行规则，third_party 例外保持上游原始字节。
回退：revert 此补强提交仅改变构建/验证工具，不影响 schema 或用户账本。

`7435e666d631f97b67b480f6df70376b7d521868`：Linux 303 passed / 13.58s；
Windows run [36756167296](https://github.com/Lorentz-Caldfilis/Cashing/actions/runs/36756167296)
303 passed / 17.44s，源码和解压各 5 次 GUI、默认数据目录两次启动、严格 manifest 检查均成功。
候选 ZIP SHA-256 `6e0a9c798053c5717fe52e200638a78ce6bc2e3fc63a899a153ad47f37f4120a`。
固定学生语料重跑：DEV agreement 20/24，明确用途 8/12；holdout agreement 7/12，明确用途 1/6；
两组错误决定 0，10 条学习/撤回均通过。合成语料不代表真实长期使用。

完整 artifact 约 50 MB，超过本地文件工具 32 MiB 上限；连接器临时 URL 下载返回 HTTP 403。
为让复核者容易取用截图/JSON，将小型 evidence 与候选 ZIP 分为两个 Actions artifacts；
仅验证成功才保留候选包，失败时仍保留诊断证据。此调整不改变应用代码或任何权限。

## 最终阶段交付（仅候选，不发布）

Windows 精确验证提交：`0623c0517295965bdeed35b7fc8602b0149ac692`。
[成功 run 36756735665](https://github.com/Lorentz-Caldfilis/Cashing/actions/runs/36756735665)。

| 检查 | 实际结果 | 证据 |
|---|---|---|
| Linux Python 3.12.14 完整回归 | 303 passed / 13.58s，源码 7435e66 | evidence/phase3-20260930/linux-tests.xml |
| Windows Server 2022 / Python 3.14.7 | 303 passed / 18.11s，源码 0623c05 | windows/tests.xml |
| Windows 源码 Qt 进程 | 5 次通过，100/125/150/200% 与重启 | windows/ci-source/verification.json |
| 解压 EXE Qt 进程 | 5 次通过，同样缩放/重启 | windows/ci-extracted/verification.json |
| 默认数据位置与正常启动 | 两次通过、合成账本保留 | 同上 default_mode |
| 安装目录安全 | 399 个文件，运行前后集合与内容不变 | 同上 manifest_files / install_unchanged |
| 依赖安装 | requirements-lock 安装、pip check 通过，18 项 freeze | windows/installed.txt |
| 实际 Windows 截图 | 查看了解压版 Review、空态及 200% Capture | windows/windows-*.png |
| 分类固定语料 | DEV 8/12、holdout 1/6 明确用途；错误决定均 0；10 条学习/撤回通过 | classification-final.json |
| 有限历史模式审计 | 431 blob；无密钥/SQLite 头命中；1 处脚本正则误报 | repository-audit.json |

表内短证据路径以 `docs/development/evidence/phase3-20260930/` 为根。
200% 截图在 runner 的有限屏幕高度下进入可滚动紧凑模式；不能据此宣称真实跨屏或设备体验已验收。

[小型证据 artifact](https://github.com/Lorentz-Caldfilis/Cashing/actions/runs/36756735665/artifacts/11117720434)
535,795 bytes，已下载并本地核对 SHA-256：
`fc0210418a84c9e00ee1e7715eda49d99129a422784b3ac30d8e59d92ec59a6c`。
核对其中 source-commit、JUnit、两份 verification.json 与截图；归档文本在仓库中统一 LF，PNG 保持原字节。
原始 artifact 包含合成日志；仓库只保留 JSON、JUnit、依赖清单和选定截图，不提交数据库或日志。

[候选二进制 artifact](https://github.com/Lorentz-Caldfilis/Cashing/actions/runs/36756735665/artifacts/11117795401)
内含 `Cashing-candidate-0623c0517295-windows.zip` 及其摘要。
内层候选 ZIP SHA-256（由 Windows 打包脚本计算，未在本地重新下载大包计算）：
`aab9359d06b3d0a3566b49988a7592793023e48405b436b5bd7172b92a5f921b`。
外层 Actions artifact 摘要与内层 ZIP 不同，详见 windows-run.json，勿混用。
两个 artifacts 到期时间约 2026-10-14；需要复核时应及时下载。

[用户指南](../USER_GUIDE.md)、[构建与解压验收](../WINDOWS_CANDIDATE.md)、
[依赖/资源来源](../THIRD_PARTY.md)、[资料审计](REPOSITORY_AUDIT.md)及
[尚未执行的人工验收表](../MANUAL_ACCEPTANCE.md)已补齐。
新增 issue / PR 模板，不改变许可；源代码公开决定、Qt/MS 再分发义务复核和人工设备验收仍是剩余门槛。

本交付后仅追加文档与证据，不更改已验证的应用、测试或构建代码。
文档归档提交使用 `[skip ci]` 避免相同源码再次完整构建；验证对象明确固定为上述 0623c05，
不能声称后续文档提交已经生成另一个新包。草稿 PR 保持，不合并、不发 Release、不改 main。

## 第三阶段回退索引

- `7fda6b5`：平台词安全回退；撤销它会重新引入误判，不建议。
- `dcb7107`：Windows CI 入口；可 revert 移除自动化，不影响应用数据。
- `36f04b1`：Windows 备份 fsync 修复；撤销会恢复 Windows 失败，仅用于定位。
- `debe879`：可追溯打包、许可证来源和用户指南；可 revert，先回退依赖它的后续构建修改。
- `56f8ec5`：构建来源与完整安装 manifest 验证；可独立 revert，无 schema 变化。
- `7435e66`：贡献模板和有限隐私审计；仅工具/文档，可 revert。
- `0623c05`：分离小型证据 artifact；可 revert 恢复合并 artifact。

多批回退按从新到旧，保留已经生成的备份；不 reset main 或强推。所有者尚未授权公开发布。
