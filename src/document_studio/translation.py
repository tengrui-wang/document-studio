from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from lxml import etree
from docx.oxml.ns import qn

from .common import check_cancel
from .storage import atomic_json
from .word_tools import assign_text, text_groups


def digest_file(source: Path):
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def translate_docx(source: Path, dest: Path, options, client, cache_dir: Path, progress, cancel):
    size = max(200, min(6000, int(options.get("chunk_size", 2500))))
    fragment_limit = min(size, 1200)
    identity = {"sha256": options.get("_source_sha256") or digest_file(source), "endpoint": client.base, "protocol": client.provider,
                "model": options["model"], "source": options["source_lang"],
                "target": options["target_lang"], "glossary": options.get("glossary", ""),
                "fragment_limit": fragment_limit, "converter": options.get("_converter", "docx"), "schema": 1}
    signature = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    checkpoint = cache_dir / f"{signature}.json"
    cache = {"identity": identity, "translations": {}}
    if checkpoint.exists():
        try:
            loaded = json.loads(checkpoint.read_text(encoding="utf-8"))
            if loaded.get("identity") == identity and isinstance(loaded.get("translations"), dict):
                cache = loaded
        except (OSError, ValueError):
            pass
    trees, groups, entries = {}, [], []
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        if len(infos) > 10000 or sum(info.file_size for info in infos) > 300 * 1024 * 1024:
            raise ValueError("Word 文件解压后过大，当前限制为 300 MB。")
        names = set(archive.namelist())
        if "word/document.xml" not in names or any("vbaProject" in name for name in names):
            raise ValueError("仅支持无宏的标准 DOCX 文件。")
        for name in archive.namelist():
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            if not (name == "word/document.xml" or Path(name).name.startswith(("header", "footer", "footnotes", "endnotes"))):
                continue
            parser = etree.XMLParser(resolve_entities=False, no_network=True)
            tree = etree.fromstring(archive.read(name), parser)
            if any(tree.iter(qn("w:ins"))) or any(tree.iter(qn("w:del"))):
                raise ValueError("文档包含未接受的修订。请在 Word 中接受或拒绝修订后再翻译，避免段落歧义。")
            trees[name] = tree
            for paragraph in tree.iter(qn("w:p")):
                for nodes in text_groups(paragraph):
                    text = "".join(node.text or "" for node in nodes)
                    if not text.strip():
                        continue
                    # Stable ids depend on document content, not the API batching limit.
                    group_id = len(groups)
                    fragments = [text[start:start + fragment_limit] for start in range(0, len(text), fragment_limit)]
                    ids = []
                    for fragment_id, fragment in enumerate(fragments):
                        ident = f"p{group_id}s{fragment_id}"
                        entries.append({"id": ident, "text": fragment})
                        ids.append(ident)
                    groups.append((nodes, ids))
        if not entries:
            raise ValueError("DOCX 中没有可翻译正文。图片内文字、域和公式不参与翻译。")
        pending = []
        for entry in entries:
            existing = cache["translations"].get(entry["id"])
            if not isinstance(existing, str) or not existing.strip():
                pending.append(entry)
        completed = len(entries) - len(pending)
        progress(int(85 * completed / len(entries)), f"翻译断点：已恢复 {completed}/{len(entries)} 分块")
        cursor = 0
        while cursor < len(pending):
            check_cancel(cancel)
            batch, length = [], 0
            while cursor < len(pending):
                entry = pending[cursor]
                if batch and length + len(entry["text"]) > size:
                    break
                batch.append(entry)
                length += len(entry["text"])
                cursor += 1
            translated = client.translate(options["model"], batch, options["source_lang"],
                                          options["target_lang"], options.get("glossary", ""))
            for item in translated:
                cache["translations"][item["id"]] = item["text"]
            atomic_json(checkpoint, cache)
            completed += len(batch)
            progress(int(85 * completed / len(entries)), f"已翻译并保存断点 {completed}/{len(entries)}")
        check_cancel(cancel)
        for nodes, ids in groups:
            assign_text(nodes, "".join(cache["translations"][ident] for ident in ids))
        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for info in infos:
                check_cancel(cancel)
                data = (etree.tostring(trees[info.filename], xml_declaration=True, encoding="UTF-8", standalone=True)
                        if info.filename in trees else archive.read(info.filename))
                output.writestr(info, data)
    progress(95, "段落数量与顺序校验完成；请复核译文和排版")
