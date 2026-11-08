"""
Digital Microscope — Core Engine v2.0
Universal analyzer of digital tissue at the molecular level.
"""

from __future__ import annotations

import ast
import csv
import io
import json
import re
import os
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class Molecule:
    """Elementary unit of digital tissue."""
    id: str
    type: str
    name: str
    value: Optional[str] = None
    children: List["Molecule"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    edges: List[Dict[str, str]] = field(default_factory=list)  # for graph view

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "value": self.value,
            "metadata": self.metadata,
            "children": [c.to_dict() for c in self.children],
            "edges": self.edges,
        }

    def flatten(self) -> List["Molecule"]:
        result = [self]
        for c in self.children:
            result.extend(c.flatten())
        return result


class DigitalMicroscope:
    """Professional universal digital tissue analyzer."""

    SUPPORTED = {
        "json", "python", "csv", "yaml", "html", "markdown", "xml",
        "text", "toml", "ini", "log", "directory"
    }

    def __init__(self):
        self._counter = 0

    def _id(self) -> str:
        self._counter += 1
        return f"m{self._counter}"

    def analyze(
        self,
        content: Union[str, bytes, Path],
        filename: Optional[str] = None,
        force_type: Optional[str] = None,
    ) -> Molecule:
        if isinstance(content, Path):
            if content.is_dir():
                return self._analyze_directory(content)
            filename = filename or content.name
            content = content.read_bytes()

        if isinstance(content, bytes):
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1", errors="replace")
        else:
            text = str(content)

        detected = force_type or self._detect(text, filename)
        method = getattr(self, f"_analyze_{detected}", self._analyze_text)
        root = method(text, filename or "sample")
        root.metadata.update({
            "detected_type": detected,
            "size_bytes": len(text.encode("utf-8", errors="replace")),
            "lines": text.count("\n") + 1,
            "chars": len(text),
        })
        return root

    def _detect(self, text: str, filename: Optional[str]) -> str:
        if filename:
            ext = Path(filename).suffix.lower()
            mapping = {
                ".py": "python", ".json": "json", ".csv": "csv", ".tsv": "csv",
                ".yaml": "yaml", ".yml": "yaml", ".html": "html", ".htm": "html",
                ".md": "markdown", ".markdown": "markdown", ".xml": "xml",
                ".toml": "toml", ".ini": "ini", ".log": "log", ".txt": "text",
            }
            if ext in mapping:
                return mapping[ext]

        s = text.strip()
        if s.startswith(("{", "[")):
            try:
                json.loads(s)
                return "json"
            except Exception:
                pass
        if s.startswith(("<?xml", "<html", "<!DOCTYPE")):
            return "xml" if "<?xml" in s[:200] else "html"
        if any(k in text for k in ("def ", "class ", "import ", "from ")):
            try:
                ast.parse(text)
                return "python"
            except SyntaxError:
                pass
        if re.search(r"^\[.+\]", text, re.M) and "=" in text:
            return "ini"
        if "\n" in text and "," in text and not text.strip().startswith("#"):
            return "csv"
        return "text"

    # ---------- Analyzers ----------

    def _analyze_json(self, text: str, name: str) -> Molecule:
        try:
            data = json.loads(text)
        except Exception as e:
            return Molecule(self._id(), "error", name, str(e))
        root = Molecule(self._id(), "json_document", name, metadata={"root_type": type(data).__name__})
        self._walk_json(data, root)
        return root

    def _walk_json(self, obj: Any, parent: Molecule, key: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                node = Molecule(self._id(), "object", str(k), parent_id=parent.id)
                parent.children.append(node)
                self._walk_json(v, node, k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                node = Molecule(self._id(), "array", f"[{i}]", parent_id=parent.id)
                parent.children.append(node)
                self._walk_json(item, node)
        else:
            parent.children.append(Molecule(
                self._id(), "value", key or "value",
                str(obj)[:500],
                metadata={"python_type": type(obj).__name__, "length": len(str(obj))},
                parent_id=parent.id
            ))

    def _analyze_python(self, text: str, name: str) -> Molecule:
        try:
            tree = ast.parse(text)
        except SyntaxError as e:
            return Molecule(self._id(), "error", name, f"SyntaxError: {e}")

        root = Molecule(self._id(), "python_module", name)
        imports, functions, classes, other = [], [], [], []

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(node)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node)
            elif isinstance(node, ast.ClassDef):
                classes.append(node)

        if imports:
            imp_node = Molecule(self._id(), "imports", "imports")
            for imp in imports:
                if isinstance(imp, ast.Import):
                    for alias in imp.names:
                        imp_node.children.append(Molecule(self._id(), "import", alias.name, alias.asname))
                else:
                    module = imp.module or ""
                    for alias in imp.names:
                        imp_node.children.append(Molecule(self._id(), "import_from", f"{module}.{alias.name}", alias.asname))
            root.children.append(imp_node)

        if classes:
            cls_node = Molecule(self._id(), "classes", "classes")
            for cls in classes:
                c = Molecule(self._id(), "class", cls.name, metadata={"bases": [ast.unparse(b) if hasattr(ast, "unparse") else str(b) for b in cls.bases], "lineno": cls.lineno})
                for item in cls.body:
                    if isinstance(item, ast.FunctionDef):
                        c.children.append(Molecule(self._id(), "method", item.name, metadata={"args": [a.arg for a in item.args.args], "lineno": item.lineno}))
                cls_node.children.append(c)
            root.children.append(cls_node)

        if functions:
            fn_node = Molecule(self._id(), "functions", "functions")
            for fn in functions:
                fn_node.children.append(Molecule(
                    self._id(), "function", fn.name,
                    metadata={"args": [a.arg for a in fn.args.args], "lineno": fn.lineno, "decorators": len(fn.decorator_list)}
                ))
            root.children.append(fn_node)

        # Full AST summary
        ast_node = Molecule(self._id(), "ast_summary", "ast")
        types = Counter(type(n).__name__ for n in ast.walk(tree))
        for t, c in types.most_common(15):
            ast_node.children.append(Molecule(self._id(), "ast_node", t, str(c)))
        root.children.append(ast_node)
        return root

    def _analyze_text(self, text: str, name: str) -> Molecule:
        root = Molecule(self._id(), "text_document", name)
        words = re.findall(r"\b[\w'-]+\b", text)
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        root.metadata.update({
            "word_count": len(words),
            "unique_words": len({w.lower() for w in words}),
            "sentence_count": len(sentences),
            "avg_sentence_len": round(len(words) / max(len(sentences), 1), 1),
        })

        if sentences:
            sent_node = Molecule(self._id(), "sentences", "sentences")
            for i, s in enumerate(sentences[:30]):
                sent_node.children.append(Molecule(self._id(), "sentence", f"s{i+1}", s[:400]))
            root.children.append(sent_node)

        counter = Counter(w.lower() for w in words if len(w) > 2)
        if counter:
            freq = Molecule(self._id(), "word_frequency", "top_words")
            for w, c in counter.most_common(25):
                freq.children.append(Molecule(self._id(), "word", w, str(c)))
            root.children.append(freq)
        return root

    def _analyze_csv(self, text: str, name: str) -> Molecule:
        root = Molecule(self._id(), "csv_table", name)
        try:
            sample = text[:4096]
            dialect = csv.Sniffer().sniff(sample) if "\n" in sample else csv.excel
            reader = csv.reader(io.StringIO(text), dialect)
            rows = list(reader)
            if not rows:
                return root
            headers = rows[0]
            root.metadata.update({"columns": len(headers), "rows": max(0, len(rows) - 1)})
            hnode = Molecule(self._id(), "headers", "columns")
            for h in headers:
                hnode.children.append(Molecule(self._id(), "column", h or "(empty)"))
            root.children.append(hnode)
            for i, row in enumerate(rows[1:16]):
                rnode = Molecule(self._id(), "row", f"row_{i+1}")
                for j, val in enumerate(row):
                    col = headers[j] if j < len(headers) else f"col{j}"
                    rnode.children.append(Molecule(self._id(), "cell", col, str(val)[:200]))
                root.children.append(rnode)
        except Exception as e:
            root.metadata["error"] = str(e)
        return root

    def _analyze_html(self, text: str, name: str) -> Molecule:
        root = Molecule(self._id(), "html_document", name)
        tags = re.findall(r"<(\w+)[^>]*>", text, re.I)
        counts = Counter(tags)
        tnode = Molecule(self._id(), "tags", "tag_frequency")
        for tag, c in counts.most_common(40):
            tnode.children.append(Molecule(self._id(), "tag", tag.lower(), str(c)))
        root.children.append(tnode)
        links = re.findall(r'href=["\']([^"\']+)["\']', text, re.I)
        if links:
            lnode = Molecule(self._id(), "links", "hyperlinks")
            for link in links[:30]:
                lnode.children.append(Molecule(self._id(), "link", link[:200]))
            root.children.append(lnode)
        root.metadata["tag_count"] = len(tags)
        return root

    def _analyze_markdown(self, text: str, name: str) -> Molecule:
        root = Molecule(self._id(), "markdown_document", name)
        headers = re.findall(r"^(#{1,6})\s+(.+)$", text, re.M)
        if headers:
            hnode = Molecule(self._id(), "structure", "headers")
            for hashes, title in headers:
                hnode.children.append(Molecule(self._id(), "header", title.strip(), f"h{len(hashes)}"))
            root.children.append(hnode)
        text_part = self._analyze_text(text, "content")
        root.children.extend(text_part.children)
        root.metadata.update(text_part.metadata)
        return root

    def _analyze_xml(self, text: str, name: str) -> Molecule:
        root = Molecule(self._id(), "xml_document", name)
        tags = re.findall(r"<(\w+)[^>]*>", text)
        counts = Counter(tags)
        for tag, c in counts.most_common(30):
            root.children.append(Molecule(self._id(), "tag", tag, str(c)))
        return root

    def _analyze_yaml(self, text: str, name: str) -> Molecule:
        try:
            import yaml
            data = yaml.safe_load(text)
            root = Molecule(self._id(), "yaml_document", name)
            self._walk_json(data, root)
            return root
        except ImportError:
            return self._analyze_text(text, name)
        except Exception as e:
            return Molecule(self._id(), "error", name, str(e))

    def _analyze_toml(self, text: str, name: str) -> Molecule:
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return self._analyze_text(text, name)
        try:
            data = tomllib.loads(text)
            root = Molecule(self._id(), "toml_document", name)
            self._walk_json(data, root)
            return root
        except Exception as e:
            return Molecule(self._id(), "error", name, str(e))

    def _analyze_ini(self, text: str, name: str) -> Molecule:
        root = Molecule(self._id(), "ini_document", name)
        current = None
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", ";")):
                continue
            if line.startswith("[") and line.endswith("]"):
                current = Molecule(self._id(), "section", line[1:-1])
                root.children.append(current)
            elif "=" in line and current:
                k, _, v = line.partition("=")
                current.children.append(Molecule(self._id(), "key", k.strip(), v.strip()))
        return root

    def _analyze_log(self, text: str, name: str) -> Molecule:
        root = Molecule(self._id(), "log_file", name)
        lines = text.splitlines()
        root.metadata["line_count"] = len(lines)
        levels = Counter()
        for line in lines:
            m = re.search(r"\b(DEBUG|INFO|WARNING|ERROR|CRITICAL|WARN)\b", line, re.I)
            if m:
                levels[m.group(1).upper()] += 1
        if levels:
            lnode = Molecule(self._id(), "log_levels", "levels")
            for lvl, c in levels.most_common():
                lnode.children.append(Molecule(self._id(), "level", lvl, str(c)))
            root.children.append(lnode)
        # sample lines
        sample = Molecule(self._id(), "sample", "first_lines")
        for i, line in enumerate(lines[:20]):
            sample.children.append(Molecule(self._id(), "line", f"L{i+1}", line[:300]))
        root.children.append(sample)
        return root

    def _analyze_directory(self, path: Path) -> Molecule:
        root = Molecule(self._id(), "directory", path.name or str(path))
        try:
            for item in sorted(path.iterdir()):
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    child = Molecule(self._id(), "directory", item.name, metadata={"path": str(item)})
                    # shallow only
                    try:
                        count = sum(1 for _ in item.iterdir())
                        child.metadata["items"] = count
                    except Exception:
                        pass
                    root.children.append(child)
                else:
                    size = item.stat().st_size
                    root.children.append(Molecule(
                        self._id(), "file", item.name,
                        metadata={"size": size, "ext": item.suffix}
                    ))
        except Exception as e:
            root.metadata["error"] = str(e)
        return root

    # ---------- Utilities ----------

    def get_stats(self, root: Molecule) -> Dict:
        types = Counter()
        total = 0
        def walk(m: Molecule):
            nonlocal total
            total += 1
            types[m.type] += 1
            for c in m.children:
                walk(c)
        walk(root)
        return {
            "total_molecules": total,
            "types": dict(types.most_common()),
            "depth": self._depth(root),
            "detected_type": root.metadata.get("detected_type"),
        }

    def _depth(self, m: Molecule, d: int = 0) -> int:
        if not m.children:
            return d
        return max(self._depth(c, d + 1) for c in m.children)

    def compare(self, a: Molecule, b: Molecule) -> Dict:
        sa, sb = self.get_stats(a), self.get_stats(b)
        return {
            "a": {"name": a.name, "type": a.metadata.get("detected_type"), "molecules": sa["total_molecules"]},
            "b": {"name": b.name, "type": b.metadata.get("detected_type"), "molecules": sb["total_molecules"]},
            "diff_molecules": sa["total_molecules"] - sb["total_molecules"],
            "common_types": list(set(sa["types"]) & set(sb["types"])),
        }

    def to_mermaid(self, root: Molecule, max_nodes: int = 40) -> str:
        lines = ["graph TD"]
        count = 0
        def walk(m: Molecule, parent_id: Optional[str] = None):
            nonlocal count
            if count >= max_nodes:
                return
            nid = m.id
            label = f"{m.type}: {m.name}"[:40].replace('"', "'")
            lines.append(f'  {nid}["{label}"]')
            count += 1
            if parent_id:
                lines.append(f"  {parent_id} --> {nid}")
            for c in m.children:
                walk(c, nid)
        walk(root)
        return "\n".join(lines)


# Convenience
def analyze(content, filename=None, force_type=None) -> Molecule:
    return DigitalMicroscope().analyze(content, filename, force_type)
