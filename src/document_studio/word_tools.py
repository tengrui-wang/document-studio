from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from .common import check_cancel


def assign_text(nodes, translated: str):
    """Keep every run and non-text XML node; distribute text over existing runs."""
    total = sum(len(node.text or "") for node in nodes)
    consumed, start = 0, 0
    for index, node in enumerate(nodes):
        consumed += len(node.text or "")
        end = len(translated) if index == len(nodes) - 1 else round(len(translated) * consumed / max(total, 1))
        node.text = translated[start:end]
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        start = end


def word_format(source: Path, dest: Path, options, progress, cancel):
    doc = Document(source)
    # Paragraph XML includes nested tables, hyperlinks, headers and textboxes.
    roots = [doc.element]
    seen = set()
    for section in doc.sections:
        for part in (section.header, section.footer, section.first_page_header,
                     section.first_page_footer, section.even_page_header, section.even_page_footer):
            if part.part.partname not in seen:
                seen.add(part.part.partname)
                roots.append(part._element)
        margin = options.get("margin_cm")
        if margin:
            section.top_margin = section.bottom_margin = section.left_margin = section.right_margin = Cm(margin)
    from docx.text.paragraph import Paragraph
    paragraphs = [Paragraph(el, doc) for root in roots for el in root.iter(qn("w:p"))]
    for index, paragraph in enumerate(paragraphs):
        check_cancel(cancel)
        if options.get("line_spacing"):
            paragraph.paragraph_format.line_spacing = options["line_spacing"]
        for key, attr in (("space_before", "space_before"), ("space_after", "space_after")):
            if options.get(key) is not None:
                setattr(paragraph.paragraph_format, attr, Pt(options[key]))
        runs = list(paragraph._p.iter(qn("w:r")))
        from docx.text.run import Run
        for element in runs:
            run = Run(element, paragraph)
            if options.get("font"):
                run.font.name = options["font"]
                run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), options["font"])
            if options.get("font_size"):
                run.font.size = Pt(options["font_size"])
        if options.get("heading_size") and paragraph.style and paragraph.style.style_id.startswith("Heading"):
            for element in runs:
                run = Run(element, paragraph)
                run.font.size = Pt(options["heading_size"])
                run.font.bold = True
        find = options.get("find", "")
        if find:
            # Replace across runs while preserving inline equations/images as boundaries.
            for nodes in text_groups(paragraph._p):
                text = "".join(n.text or "" for n in nodes)
                if find in text:
                    assign_text(nodes, text.replace(find, options.get("replace", "")))
        progress(int(90 * (index + 1) / max(1, len(paragraphs))), "修改 Word 格式")
    doc.save(dest)


def text_groups(paragraph):
    """Contiguous prose groups, excluding fields, equations and nested paragraphs."""
    protected = {qn("w:drawing"), qn("w:pict"), qn("w:object"), qn("w:fldSimple"),
                 "{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath",
                 "{http://schemas.openxmlformats.org/officeDocument/2006/math}oMathPara"}
    groups, current, field_depth = [], [], 0

    def flush():
        nonlocal current
        if current:
            groups.append(current)
            current = []

    def visit(element):
        nonlocal field_depth
        if element is not paragraph and (element.tag in protected or element.tag == qn("w:p")):
            flush()
            return
        if element.tag == qn("w:fldChar"):
            flush()
            kind = element.get(qn("w:fldCharType"))
            if kind == "begin":
                field_depth += 1
            elif kind == "end":
                field_depth = max(0, field_depth - 1)
            return
        if element.tag in (qn("w:tab"), qn("w:br"), qn("w:cr"), qn("w:instrText")):
            flush()
        elif element.tag == qn("w:t") and field_depth == 0:
            current.append(element)
        for child in element:
            visit(child)

    visit(paragraph)
    flush()
    return groups


def locate_soffice(configured=""):
    candidates = [configured, shutil.which("soffice")]
    for root in (os.environ.get("PROGRAMFILES", "C:/Program Files"),
                 os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")):
        candidates.append(str(Path(root) / "LibreOffice/program/soffice.exe"))
    return next((p for p in candidates if p and Path(p).is_file()), None)


def detect_engines(configured=""):
    word = False
    if os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Word.Application\\CLSID") as key:
                identifier = winreg.QueryValueEx(key, "")[0]
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"CLSID\\{identifier}\\LocalServer32") as key:
                command = winreg.QueryValueEx(key, "")[0]
            import re
            match = re.match(r'^\s*"?(.+?\.exe)"?(?:\s|$)', command, re.IGNORECASE)
            word = bool(match and Path(os.path.expandvars(match[1])).is_file())
        except OSError:
            pass
    return {"word": word, "libreoffice": locate_soffice(configured)}


def word_to_pdf(source: Path, dest: Path, options, progress, cancel):
    check_cancel(cancel)
    # Word can fetch remote templates/OLE links while opening a DOCX. Fail closed.
    import zipfile
    from lxml import etree
    with zipfile.ZipFile(source) as archive:
        if sum(item.file_size for item in archive.infolist()) > 300 * 1024 * 1024:
            raise ValueError("Word 文件解压后过大，当前限制为 300 MB。")
        for name in archive.namelist():
            if name.endswith(".rels"):
                relationships = etree.fromstring(archive.read(name), etree.XMLParser(resolve_entities=False, no_network=True))
                for relationship in relationships:
                    if relationship.get("TargetMode") == "External" and not relationship.get("Type", "").endswith("/hyperlink"):
                        raise ValueError("文档含外部模板、链接图片或 OLE 资源，请在 Word 中断开外部链接后转换，以确保本地处理。")
    backend = options.get("backend", "auto")
    if backend in ("auto", "word") and os.name == "nt":
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        app, doc, old_update_links = None, None, None
        try:
            try:
                app = win32com.client.DispatchEx("Word.Application")
            except Exception:
                if backend == "word":
                    raise ValueError("未检测到可用的 Microsoft Word，请安装 Word 或选择 LibreOffice。") from None
            if app is not None:
                progress(20, "通过 Microsoft Word 导出 PDF")
                app.Visible = False
                app.DisplayAlerts = 0
                app.AutomationSecurity = 3  # force-disable macros
                old_update_links = app.Options.UpdateLinksAtOpen
                app.Options.UpdateLinksAtOpen = False
                doc = app.Documents.Open(str(source.resolve()), ReadOnly=True, AddToRecentFiles=False,
                                         ConfirmConversions=False)
                check_cancel(cancel)
                doc.ExportAsFixedFormat(str(dest.resolve()), 17)
                if not dest.is_file() or not dest.stat().st_size:
                    raise ValueError("Microsoft Word 未生成有效 PDF，请检查文档。")
                return
        except pythoncom.com_error:
            raise ValueError("Microsoft Word 导出失败。请检查 Word 激活状态、文件权限和文档是否可正常打开，或改用 LibreOffice。") from None
        finally:
            try:
                if doc is not None:
                    doc.Close(False)
            finally:
                try:
                    if app is not None:
                        try:
                            if old_update_links is not None:
                                app.Options.UpdateLinksAtOpen = old_update_links
                        finally:
                            app.Quit()
                finally:
                    pythoncom.CoUninitialize()
    executable = locate_soffice(options.get("soffice", ""))
    if not executable:
        raise ValueError("Word 转 PDF 需要本机 Microsoft Word 或 LibreOffice。请安装任一软件；Document Studio 本身无需 Python。")
    progress(20, "通过 LibreOffice 导出 PDF")
    profile = dest.parent / "lo-profile"
    command = [executable, f"-env:UserInstallation={profile.resolve().as_uri()}", "--headless",
               "--convert-to", "pdf", "--outdir", str(dest.parent), str(source.resolve())]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
    start = time.monotonic()
    try:
        while process.poll() is None:
            check_cancel(cancel)
            if time.monotonic() - start > 180:
                raise ValueError("LibreOffice 转换超时，请检查文档或改用 Word。")
            time.sleep(.2)
        produced = dest.parent / f"{source.stem}.pdf"
        if process.returncode or not produced.exists():
            raise ValueError("LibreOffice 未生成 PDF，请检查文档是否损坏或受密码保护。")
        if produced != dest:
            produced.rename(dest)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
