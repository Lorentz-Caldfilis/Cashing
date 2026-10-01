# 随包动态库及对应源码

Cashing 源码采用 MIT；PySide6/shiboken6 和本包所用 Qt 库按 LGPLv3 使用。第三方授权文本在 LICENSES，精确版本、源码提交、下载地址和 SHA-256 在 SOURCES/source_archives.json。SOURCES 内直接附带未修改的 6.11.2 源码归档：pyside-setup、qtbase、qtimageformats、qttranslations；无需等待维护者提供源码。

## 替换或重新构建

允许为修改这些 LGPL 库而调试、逆向分析及替换动态库。本应用不对替换后的库执行签名或摘要锁定；MANIFEST.sha256 仅供交付完整性核验，日常运行不强制匹配。替换需保持 Windows x64、Qt 6.11 的二进制接口及 Python 3.14 ABI 一致，否则可能无法启动。

1. 另存完整程序目录；关闭 Cashing。账本位于用户数据目录，不在程序文件夹。
2. 解压 SOURCES 内的归档。按各归档自带 README/CMake/构建文档，用匹配的 MSVC、CMake、Ninja、Windows SDK 构建 Qt Base；以该 Qt 构建 qtimageformats。构建 PySide6/shiboken6 时使用 Python 3.14 x64、对应 Qt 和上游要求的 libclang；原始构建脚本和绑定定义都包含在归档中。qttranslations 提供中文翻译源码。
3. 在程序副本的 `_internal` 下，替换相应 Qt DLL、PySide6/shiboken6 扩展和插件，保持原目录结构。平台插件位于 `PySide6/plugins/platforms`，图片插件位于 `PySide6/plugins/imageformats`。Qt/Python ABI 不一致时请从 Cashing 源码重建整个包，而非混用版本。
4. 用独立绝对 `--data-dir` 启动副本，确认替换后的库可运行，再决定是否用于个人账本。验证脚本的摘要门槛会拒绝修改过的发行副本；这不限制直接运行修改后的程序。

构建参考：[Qt Windows 源码构建](https://doc.qt.io/qt-6/windows-building.html)、[Qt for Python 构建](https://doc.qt.io/qtforpython-6/building_from_source/index.html)。归档中的组件许可和第三方声明适用于各自文件，不能把 Cashing 的 MIT 许可用于覆盖它们。

维护者的源码取回命令（仅构建时联网）：`python scripts/fetch_sources.py`。脚本按精确提交取回并核对 SHA-256；打包缺失归档或摘要不符会停止。旧版遗留的私人背景文件仍禁止进入发行包。
