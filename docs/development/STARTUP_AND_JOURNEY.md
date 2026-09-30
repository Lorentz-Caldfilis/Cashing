# 启动剖析与首次使用旅程

起点 3b57cd5；分页复核优先修于 014de8e。无分类词表、schema、依赖或视觉重做。

## 启动时间拆分

同一 Linux X11/100% 虚拟显示、5 vCPU、Python 3.12.14、Qt 6.11.2；使用上一阶段密集 10,000 条合成账本，
不使用真实数据。先以 perf_counter 记录导入/初始化/显示阶段，再用 cProfile 定位窗口构造和进入 Review。
表中为同一诊断脚本的累计墙钟时间，含 profiler 开销，不能直接当上一阶段无剖析的 3.59s。

| 累计里程碑 | 改动前 | 改动后 |
|---|---:|---:|
| Qt 导入 | 0.063s | 0.066s |
| 全部 UI 模块导入 | 0.100s | 0.121s |
| QApplication 建立 | 0.106s | 0.127s |
| SQLite 初始化完成 | 0.200s | 0.221s |
| 窗口构造完成 | 4.044s | 3.304s |
| Capture 首次可交互 | 4.158s | 3.355s |
| Review 首次正确统计 | 4.875s | 4.338s |

最大单项为第一次 QWidget 子控件建立：3.01s。无 Cashing 模块、仅 QApplication + 父 QWidget + 子 QWidget
的最小程序也测得首个 child 3.008s、第二个 0.000061s；系统调用跟踪观察到同区间 poll 等待。
这是本环境 Qt/xcb 初始化等待的证据，未定位到底层服务根因，不推广为所有 Windows 的启动成本。
没有关闭可访问性、改系统设置或藏到后台来抹掉该时间。预设 2s 仍未达成。

另外有可消除的应用工作：Review 构造时与首次切换时各调用 Ledger.month，一共解释 20,000 条。
改为仅在 Review 即将显示时查询，Capture 保存不再重算隐藏月份。每次进入仍从数据库重新读取，
不引入跨进程陈旧缓存；首次 Review 一共解释 10,000 条。没有工作线程或后台任务。
改动后首次 Review 本身耗时比之前更长（包含首次建行），但两个累计里程碑均诚实列出。
完整结果仍由 SQL/分类读取，分页只限制 60 个行控件；没有新增整表副本/常驻查询缓存。

可复现命令（新 label 拒绝覆盖）：

```bash
python scripts/verify_durability.py --label synthetic-profile-fixture --dense
python scripts/profile_startup.py --fixture synthetic-profile-fixture --label profile-new
```

Linux X11 设置 DISPLAY 与 QT_QPA_PLATFORM=xcb；Windows 不设置 xcb。
新的 CLI 实际运行复核为 Capture 3.354s、Review 4.390s，见 archived profile JSON；没有重复扫全套语料。
回退此批延迟加载提交即恢复原预先查询，无 schema 或数据恢复步骤。

## 连续新用户旅程

`scripts/student_journey.py --label <新名称>` 在隔离目录完成：首次启动 → 18.50 食堂午饭、15/16 两笔咖啡赶论文
→ 将一笔咖啡改为工具，另一笔自动跟随 → 撤销后两笔恢复未知且标签消失 → 再明确标注
→ 搜索找出两笔 → 通过备份菜单操作生成快照 → 关闭窗口 → 复制到全新目录 → GUI 重新打开。
恢复后总额 49.50，工具 31.00，所有事实和个人标签相同，来源仍区分自选/自动。
实际 Linux X11/100% 通过，四张连续截图和 JSON 留存。

边界：中文文本通过 Qt setText 注入，非真实 IME；文件选择器由测试提供目标，但执行真实备份菜单动作；
恢复窗口在同一进程重新建立，不称 OS 重启。已有独立 smoke/release 进程验证仍负责跨进程重启。
该旅程进入自动回归，未来 Windows CI 也执行其 offscreen Qt 路径；另有原生 Windows source/frozen GUI。

## 验证中遇到的失败

首轮全量有 2 项失败：初始化下个月按钮尚未禁用（已修）；旧测试要求隐藏 Review 即时生成行
（随明确延迟行为更新为验证存储后进入 Review 显示最新记录）。定向 25 tests 通过。
第一次 200% X11 GUI 与剖析窗口同时运行时丢失焦点；保留 FAIL JSON，并在不运行其他 X11 窗口的条件下重跑。
未删除失败记录或把失败轮计为通过。最终结果在后续证据段记录。

最有价值的剩余工作是实机 Windows 输入/跨屏/干净离线安装、开源许可证与再分发决定、最终独立复核。
不为填满剩余时限增加功能；无需继续追已知分类小集分数。

最终 Linux：406 tests / 36.32s；独占 X11 的 100%、重启、125%、150%、200% 共五个 GUI 进程全部通过。
