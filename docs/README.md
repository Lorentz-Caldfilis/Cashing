# Cashing 文档入口

阅读顺序：先看 [产品与设计约束](PRODUCT.md)，再看 [维护规范](MAINTENANCE.md)；需要判断当前版本、验收范围或远端状态时看 [状态快照](STATUS.md)。README 是使用和构建指南。

## 权威性与冲突处理

2026-09-30 起，[Student edition 限定修订](design/Student_Edition_Amendment.md)在其列明范围内优先。其余设计约束的优先级沿用原规范：

1. [设计哲学](design/Cashing_Design_Philosophy_v1.0.md)
2. [信息架构](design/Cashing_Information_Architecture_v1.0.md)
3. [交互规范](design/Cashing_Interaction_Specification_v1.0.md)
4. [审美人格](design/Cashing_Art_Direction_Product_Character_v1.0.md)
5. [视觉设计系统](design/Cashing_Visual_Design_System_v1.0.md)
6. [PC 浅色基线修订](design/Cashing_PC_Light_Visual_Baseline_Amendments_v0.1.md)
7. 视觉稿、实现便利性

`PRODUCT.md` 是便于日常决策的摘要；它不修改上述规范。规范中的未来形态不等于已实现功能。当前行为以源码和测试为准；若源码违反规范，应记录差异并修复，不能默默把实现误差写成新原则。哲学变更必须明确讨论并修改源规范。

## 其余文档

- [Student edition 开发与回退](development/STUDENT_EDITION.md)
- [第二阶段分类、独立审查修复及界面证据](development/STUDENT_PHASE2.md)
- [第三阶段 Windows、打包与审计证据](development/STUDENT_PHASE3.md)
- [第四阶段分类证据与审查修复](development/STUDENT_PHASE4.md)
- [1 万条耐用性、分页与恢复](development/STUDENT_DURABILITY.md)
- [启动剖析、最终旅程与候选验证](development/STARTUP_AND_JOURNEY.md)
- [用户可读候选摘要](CANDIDATE_SUMMARY.md)
- [初次使用、备份恢复和卸载](USER_GUIDE.md)
- [Windows 候选构建](WINDOWS_CANDIDATE.md)、[依赖与资源来源](THIRD_PARTY.md)
- [尚未执行的人工 Windows 验收表](MANUAL_ACCEPTANCE.md)
- [资料隐私审计范围与限制](development/REPOSITORY_AUDIT.md)
- [本轮验收矩阵与截图](development/STUDENT_VALIDATION.md)
- [开源准备清单](OPEN_SOURCE_READINESS.md)

- [自适应分类](development/CLASSIFICATION.md)：算法、合成基准、局限和修改门槛。
- [UI v2 实施记录](development/IMPLEMENTATION_STATUS.md)：历史里程碑与实测记录；其中较早阶段的“当前”只表示当时。
- `releases/v1.0.0/`：v1.0.0 的历史审计与使用资料，不代表 v1.1.0 状态。

外部交接说明可以作为核对线索，但不是仓库规范；文档里的版本、测试数量和 GitHub 状态均需按当前证据更新。
