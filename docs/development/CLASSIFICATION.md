# 本地分类设计

Cashing 分类器使用 Python 标准库，不调用网络、模型 API 或读取私人账本做开发评估。
三类为生活、工具、娱乐；证据不足时返回“暂未判断”。这是允许的结果，不是待办，也不影响总额。

## 保存事实，派生解释

数据库的 `category_by_user=1` 表示用户明确指定了类别，含 `(category=NULL, category_by_user=1)` 的明确暂未判断。
`category_by_user=0` 时，类别在读取时推断，不回写数据库，也不把软件判断作为学习标签。
“自动判断”移除当前个人标签；撤销必须恢复原始字段和标签来源，而非界面派生值。

## 当前实现

- `classification.py` 管理个人短语投票、近期权重、内置先验和优势门槛。
- `classification_evidence.py` 保留未知片段、强弱证据和用途组合，防止仅凭弱子串或品牌断言用途。
- `lexicon.py` 提供内置词和歧义边界。平台名、品牌及含义不明的物品不能独立决定类别。
- 用户明确的短语选择可以影响之后的判断；冲突、未知片段或不足的优势仍允许弃权。
- 个人标签被编辑、删除或撤销后，分类器同步更新；没有自动生成的训练样本。

源码与回归测试是细节依据。一次纠正不保证能够代表每一种相同商品的真实用途。

## 修改与评估

保留 `tests/test_classification*.py` 及固定合成 fixture；评估工具包括：

```powershell
.\.venv\Scripts\python.exe scripts/classification_benchmark.py
.\.venv\Scripts\python.exe scripts/student_scenarios.py
.\.venv\Scripts\python.exe scripts/classification_challenges.py
```

模拟器与固定 DEV/HOLDOUT 都是开发者编写的合成数据。精确率、覆盖率和错误决定应分开报告；
不可将已反复用于调参的样本继续称为新盲测，也不可把合成分数称为真实使用准确率。
先用 DEV 进行修改，再用未参与本轮调整的样本验证。旧基准、完整运行结果与阶段报告在 Git 历史和本机归档中，
不用于在产品首页宣传准确率。用户主动提供的匿名失败例子应转成独立回归，不读取真实账本调参。

类别匹配仍是持续开发项，优先修复确认的误判；不要为了提高覆盖率扩大弱证据推断。
