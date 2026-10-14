from __future__ import annotations

from pathlib import Path
import numpy as np
import pymupdf as fitz

from .common import check_cancel, page_numbers


def open_pdf(path):
    doc = fitz.open(path)
    if doc.needs_pass:
        doc.close()
        raise ValueError("PDF 已加密，请先使用可信软件解密后再处理。")
    if not doc.page_count:
        doc.close()
        raise ValueError("PDF 没有可处理页面。")
    return doc


def pdf_to_word(source: Path, dest: Path, progress, cancel):
    with open_pdf(source) as doc:
        for index, page in enumerate(doc):
            check_cancel(cancel)
            if len(page.get_text().strip()) < 5 and page.get_images():
                raise ValueError(f"第 {index + 1} 页疑似扫描页。当前未内置 OCR，请先进行文字识别。")
    progress(10, "正在解析 PDF 排版；复杂表格、公式和多栏需人工检查")
    from pdf2docx import Converter
    converter = Converter(str(source))
    try:
        # Upstream otherwise silently skips pages that fail parsing.
        converter.convert(str(dest), multi_processing=False, ignore_page_error=False, raw_exceptions=True)
    finally:
        converter.close()
    check_cancel(cancel)
    progress(95, "已生成 Word，正在保存")


def render_processed(page, dpi=144, threshold=180, monochrome=False, preserve_images=True, enhance_text=False):
    scale = dpi / 72
    if page.rect.width * page.rect.height * scale * scale > 25_000_000:
        raise ValueError("页面过大，请降低 DPI（单页限制 2500 万像素）。")
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
    pixels = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).copy()
    original = pixels.copy() if preserve_images else None
    minimum = pixels.min(axis=2)
    # Pale background removal leaves dark glyphs and saturated marks intact.
    pixels[minimum >= threshold] = 255
    if enhance_text:
        maximum = pixels.max(axis=2)
        pixels[(maximum <= 110) & ((maximum.astype(np.int16) - pixels.min(axis=2)) <= 35)] = 0
    if monochrome:
        gray = (pixels[..., 0].astype(np.float32) * .299 + pixels[..., 1] * .587 + pixels[..., 2] * .114)
        pixels[:] = np.where(gray[..., None] >= threshold, 255, 0)
    if preserve_images:
        for image in page.get_image_info():
            rect = (fitz.Rect(image["bbox"]) * page.rotation_matrix) & page.rect
            if rect.is_empty:
                continue
            x0 = max(0, int((rect.x0 - page.rect.x0) * scale))
            y0 = max(0, int((rect.y0 - page.rect.y0) * scale))
            x1 = min(pix.width, int((rect.x1 - page.rect.x0) * scale + 1))
            y1 = min(pix.height, int((rect.y1 - page.rect.y0) * scale + 1))
            pixels[y0:y1, x0:x1] = original[y0:y1, x0:x1]
    return fitz.Pixmap(fitz.csRGB, pix.width, pix.height, pixels.tobytes(), False)


def process_pdf(operation, sources, stage: Path, options, progress, cancel):
    outputs = []
    if operation == "merge":
        with fitz.open() as out:
            for i, source in enumerate(sources):
                check_cancel(cancel)
                with open_pdf(source) as doc:
                    out.insert_pdf(doc)
                progress(int(90 * (i + 1) / len(sources)), f"合并 {i + 1}/{len(sources)}")
            target = stage / "merged.pdf"
            out.save(target, garbage=3, deflate=True)
            outputs.append(target)
        return outputs
    source = Path(sources[0])
    with open_pdf(source) as doc:
        pages = page_numbers(options.get("pages", ""), len(doc))
        if operation == "extract_text":
            chunks = []
            for i, number in enumerate(pages):
                check_cancel(cancel)
                chunks.append(f"\n--- 第 {number + 1} 页 ---\n" + doc[number].get_text(sort=True))
                progress(int(90 * (i + 1) / len(pages)), "提取文本")
            target = stage / f"{source.stem}_text.txt"
            target.write_text("".join(chunks), encoding="utf-8")
            outputs.append(target)
        elif operation == "extract_images":
            seen = set()
            for i, number in enumerate(pages):
                check_cancel(cancel)
                for image in doc[number].get_images(full=True):
                    xref = image[0]
                    if xref in seen:
                        continue
                    seen.add(xref)
                    item = doc.extract_image(xref)
                    target = stage / f"{source.stem}_p{number + 1}_img{xref}.{item['ext']}"
                    target.write_bytes(item["image"])
                    outputs.append(target)
                progress(int(90 * (i + 1) / len(pages)), "提取嵌入图片")
            if not outputs:
                raise ValueError("所选页面没有可提取的嵌入位图；矢量图不属于图片提取范围。")
        elif operation == "split":
            size = int(options.get("split_size", 1))
            if size < 1:
                raise ValueError("拆分页数必须大于零。")
            for start in range(0, len(pages), size):
                check_cancel(cancel)
                with fitz.open() as out:
                    for number in pages[start:start + size]:
                        out.insert_pdf(doc, from_page=number, to_page=number)
                    target = stage / f"{source.stem}_part{start // size + 1}.pdf"
                    out.save(target, garbage=3, deflate=True)
                    outputs.append(target)
                progress(int(90 * min(start + size, len(pages)) / len(pages)), "拆分页面")
        elif operation in ("extract_pages", "rotate", "whiten"):
            with fitz.open() as out:
                selection = pages if operation != "rotate" else list(range(len(doc)))
                for i, number in enumerate(selection):
                    check_cancel(cancel)
                    if operation == "whiten":
                        pix = render_processed(doc[number], int(options.get("dpi", 144)),
                                               int(options.get("threshold", 180)),
                                               options.get("monochrome", False),
                                               options.get("preserve_images", True), options.get("enhance_text", False))
                        if options.get("keep_text", False):
                            if not doc[number].get_text().strip():
                                raise ValueError(f"第 {number + 1} 页没有原始文字层，无法保留搜索；当前模式不提供 OCR。")
                            out.insert_pdf(doc, from_page=number, to_page=number)
                            page = out[-1]
                            if page.rotation:
                                page.remove_rotation()
                        else:
                            page = out.new_page(width=doc[number].rect.width, height=doc[number].rect.height)
                        page.insert_image(page.rect, pixmap=pix)
                    else:
                        out.insert_pdf(doc, from_page=number, to_page=number)
                        if operation == "rotate" and number in pages:
                            out[-1].set_rotation((doc[number].rotation + int(options.get("angle", 90))) % 360)
                    progress(int(90 * (i + 1) / len(selection)), f"处理第 {number + 1} 页")
                target = stage / f"{source.stem}_{operation}.pdf"
                out.save(target, garbage=3, deflate=True)
                outputs.append(target)
        else:
            raise ValueError("不支持此 PDF 操作。")
    return outputs
