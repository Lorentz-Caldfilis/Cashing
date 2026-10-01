# 第三方依赖与资源来源

Cashing 源码自 2026-10-01 经所有者授权采用 MIT，版权署名 Lorentz-Caldfilis。第三方文本仅适用于对应组件；本项目的 MIT 不能覆盖 Qt、Python 等组件的原许可。

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
1.2.0 的 spec 限制到 Core/GUI/Widgets、Network/OpenGL/Test 依赖与 Windows 平台、原生样式、JPEG/GIF/ICO/WebP 图片插件，不携带 QML/Quick、PDF、SVG 和 VirtualKeyboard 插件。最终真实文件以 BUNDLED_FILES 为准。
随包 SOURCES 直接提供 Qt Base、Qt Image Formats、Qt Translations、PySide/shiboken6 6.11.2 的精确提交源码归档，摘要保存在 `third_party/source_archives.json`；打包核对每个归档，缺失则拒绝发行。Qt Image Formats 的第三方声明随原源码归档保留，另提取所用 WebP 插件的授权文本到 LICENSES/upstream。
动态库可替换，应用无签名或摘要锁定，不限制为修改 LGPL 库进行调试和逆向分析；构建和替换说明随包提供，见 [动态库说明](LIBRARY_REPLACEMENT.md)。Windows C 运行库来自构建 Python/PySide 的发行输入，保留原始来源及文件摘要，不把 Microsoft DLL 重新标为 MIT。上述为工程再分发措施，不声称法律认证。

## 界面资源

环形图、界面控件与装饰由本仓库 QPainter/UI 绘制。应用图标是本轮内置 imagegen 生成的原创二次元极简图像；原 PNG、运行 PNG、多尺寸 ICO 和完整提示词/工具/摘要记录在 `assets/`，转换脚本只改变分辨率及容器。未仿制既有角色或商标；AI 生成资产不宣称独占版权保障。
中文字体由操作系统提供，不随包复制系统字体。`qtbase_zh_CN.qm` 来自相同版本 PySide6 的
Qt translations 目录，其上游是 [qttranslations v6.11.2](https://github.com/qt/qttranslations/tree/v6.11.2)。
开发验收截图由仓库脚本生成，仅含合成消费与合成错误内容，不含真实学生账本。
