# 第二轮高级功能取舍

已实现且有必要测试：白化后保留原文字层（覆盖图像、保持搜索/复制），旋转页图片保护，译文 DOCX → PDF（依赖已有 Word/LibreOffice）。没有重写 PDF 布局引擎。

OCR 暂不交付：本机未检测到 Tesseract。PyMuPDF 官方 [OCR 方案](https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html) 依赖外部 Tesseract 与语言数据，中英文需 eng/chi_sim。后续应提供可选本地 OCR 引擎与语言包检测，使用识别产生的文字层送入转换；不应为本轮验证安装共享软件，也不能把未经测试的 OCR 开关作为完成项。Tesseract 不是本地大语言模型，但识别质量、文字位置和扫描表格需专门样本验收。

原版式翻译暂不交付：已有 [PDFMathTranslate](https://github.com/PDFMathTranslate/PDFMathTranslate) / BabelDOC 调研，成熟方案按 AGPL 等许可复用可行，但当前工程 Python 3.13 与其 3.11/3.12 环境/布局依赖存在集成成本；用户不部署本地 LLM。后续优先可选隔离后端，云端翻译、保留公式/布局，不混入本轮稳定更新链路。

文字层保留限制：原始内容仍存在文件中，只是被处理图像覆盖，不是 PDF 清理/脱敏；不为无文字扫描页制造“可搜索”假象。视觉效果、文件大小和各阅读器搜索体验仍需后续真实样本扩展验证。
