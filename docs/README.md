# Cashing 文档

## 使用

- [软件介绍与下载（English）](../README.md) · [简体中文](../README.zh-CN.md)
- [使用指南](USER_GUIDE.md)：录入、纠错、快捷键、备份、恢复和卸载。

## 开发与维护

- [产品设计原则](PRODUCT.md)：现行产品边界、设计哲学和交互约束。
- [开发指南](development/DEVELOPER_GUIDE.md)：代码分层、运行、测试和打包。
- [维护规范](MAINTENANCE.md)：数据安全、迁移、验证与文档规则。
- [分类设计](development/CLASSIFICATION.md)：本地判断、个人标签和合成评估的局限。
- [当前版本](STATUS.md)：1.2.0 的构建身份、验证来源与支持边界。
- [Windows 构建验证](WINDOWS_CANDIDATE.md)
- [第三方依赖](THIRD_PARTY.md)、[动态库替换](LIBRARY_REPLACEMENT.md)

## 文档约定

仓库首页 `README.md` 默认使用英语，`README.zh-CN.md` 提供中文版本；两份文档开头互相链接。功能、版本、下载地址、使用范围和源码命令应保持一致。首页语言切换不代表软件界面或其余指南已经提供英语翻译。

`PRODUCT.md` 收拢此前设计规范及已授权修订，是现行产品约束入口；维护规则以 `MAINTENANCE.md` 为准。
实现行为应与约束一致，发现差异先记录和修复，不能把实现误差写成新原则。
产品哲学变更应明确说明并修改产品约束；计划不能写成已实现，未来形态不能当成当前能力。

当前目录只维护 1.2.0 所需资料。旧阶段报告、历史截图和旧版本审计已从当前目录撤出，
原件保存在本机归档及 Git 历史中。日常结果保存在忽略的 `work/` 或 CI artifact，
只有改变长期产品、操作或验证知识时才更新对应文档；不把逐次开发日志放到 README。
