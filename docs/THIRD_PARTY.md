# 第三方依赖与资源来源

本清单不改变 Cashing 的许可。Cashing 源码尚未授予公开开源许可；不得据此公开发行候选包。
第三方文本仅适用于对应第三方组件，不是项目新增的源代码许可证。

## 收集方式与边界

`package_release.py` 将构建环境各 distribution 的名称、版本与原始授权声明写入 `BUILD_DEPENDENCIES.json`，
并收集 wheel 附带的 LICENSE/COPYING 文件；构建依赖列表不等于全部被打包的运行依赖。
构建前后核对 Python、依赖版本/metadata/RECORD 与授权文本摘要，保存在 BUILD_ENVIRONMENT.json；
BUNDLED_FILES.json 单独记录实际冻结运行文件与摘要。更换构建环境或改动 dist 后必须重新构建。
Python 的原始 LICENSE 和 PyInstaller 的 COPYING（含 bootloader exception）必须存在，否则打包失败。
实际打包文件全部列于 `MANIFEST.sha256`；源码 SHA、Python 和 PySide6 版本列于 `BUILD_INFO.json`。

本环境的 PySide6/Essentials/Addons/shiboken6 wheel 没有独立许可证文件，因此另收集官方 v6.11.2
源码中的许可证文本，以及 Qt Base 的全部 57 份第三方 attribution 和其引用的许可证文件。
`LICENSES/upstream/sources.json`（源码树为 `third_party/sources.json`）记录每个原始文件的
精确上游 commit URL 与 SHA-256；打包前逐一验证，仅复制清单允许的文件，不复制本地未列出的文件；拒绝链接和不安全路径。
最终 staging 再扫描私密文件；不从网络临时补取文本。
Qt Base 清单包括未必用于 Windows 的可选组件，不能据此推断候选包含全部组件。

## 主要组件

| 组件 | 用途与来源 | 授权资料 |
|---|---|---|
| CPython | Python 标准库与运行库 | 构建 Python 的 LICENSE，含随附组件声明 |
| PySide6 / shiboken6 6.11.2 | Qt Python 绑定 | 官方 pyside-setup v6.11.2 LICENSES；wheel 的授权表达式另保留 |
| Qt 6.11.2 | Core / GUI / Widgets、平台插件与中文翻译 | Qt Base v6.11.2 LICENSES 和第三方 attribution；使用动态库 |
| PyInstaller | 冻结程序与启动器 | 安装包 COPYING，含 GPL bootloader exception |
| 测试/构建依赖 | pytest、pytest-qt、hooks 等 | 实际版本与原声明见 BUILD_DEPENDENCIES.json；随附文本原样保留 |

上游说明：[Qt for Python 授权资料](https://doc.qt.io/qtforpython-6/licenses.html)、
[Qt 开源义务](https://www.qt.io/licensing/open-source-lgpl-obligations)、
[PyInstaller 授权](https://pyinstaller.org/en/stable/license.html)。
复制许可证不等于完成所有再分发义务。公开前仍需按实际 DLL/插件核对第三方覆盖、
Qt 对应源代码提供方式及替换/重新链接要求、Microsoft 运行库条款，以及项目自身许可。
当前保留完整动态库目录，不加密、签名锁定或限制用户替换 Qt 库；尚未声称完成法律合规验收。

## 界面资源

环形图、图标和装饰由本仓库 QPainter/UI 代码绘制，没有下载插画、商标或字体。
中文字体由操作系统提供，不随包复制系统字体。`qtbase_zh_CN.qm` 来自相同版本 PySide6 的
Qt translations 目录，其上游是 [qttranslations v6.11.2](https://github.com/qt/qttranslations/tree/v6.11.2)。
开发验收截图由仓库脚本生成，仅含合成消费与合成错误内容，不含真实学生账本。
