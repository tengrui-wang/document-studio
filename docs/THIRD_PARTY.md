# 第三方许可与分发

本项目 AGPL-3.0-or-later。分发二进制须提供对应版本完整源码与构建说明。本仓库不包含商业版 MuPDF/Office 许可。

| 依赖 | 许可 | 用途 |
| --- | --- | --- |
| PyMuPDF / MuPDF | AGPL-3.0 或商业许可 | PDF 读写、提取、渲染 |
| pdf2docx | MIT | PDF → DOCX |
| python-docx | MIT | DOCX 格式操作 |
| PySide6 / Qt / Shiboken | LGPL-3.0 / GPL / 商业，按各组件许可 | UI；使用 Widgets/Core/Gui |
| httpx/httpcore | BSD-3-Clause | HTTPS API |
| keyring | MIT | Windows Credential Manager |
| pywin32 | PSF 等（见发行许可） | Word COM |
| lxml | BSD（包含 libxml2/libxslt 许可） | XML |
| NumPy | BSD-3-Clause 等 | 图像处理 |
| OpenCV headless | Apache-2.0 等 | pdf2docx 依赖 |
| fonttools | MIT | pdf2docx 依赖 |
| packaging | Apache-2.0 / BSD-2-Clause | 版本比较 |
| PyInstaller | GPL-2.0-or-later + bootloader exception | 打包，不改变应用自身许可 |

构建脚本收集**实际安装发行包**内 LICENSE/COPYING/NOTICE/COPYRIGHT 原文和元数据，放在应用 third_party 中。具体许可以原文为准；Python 与 Qt 运行时许可随对应依赖保留。Qt DLL 不采用单文件静态嵌入，保留可替换动态库。PDFMathTranslate 仅研究，未打包或复制其代码。Word/LibreOffice 不分发，需用户已有安装。

Qt LGPL/GPL 文本另附 docs/licenses。Qt 6.8.3 对应源代码可从 [官方归档](https://download.qt.io/archive/qt/6.8/6.8.3/single/) 获取，PySide6/Shiboken 对应源代码见 [pyside-setup v6.8.3](https://code.qt.io/cgit/pyside/pyside-setup.git/tree/?h=v6.8.3)。各 Python 依赖对应版本源码可从 PyPI 的同版本 Source Distribution 或其上游仓库获取，版本清单随软件附带。不对 LGPL 组件的修改、替换或为此调试进行限制。
