"""
Digital Microscope — Professional CLI
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.tree import Tree
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from microscope.core import DigitalMicroscope

console = Console() if HAS_RICH else None


def render_tree(m, max_children=25, max_depth=6, depth=0):
    if not HAS_RICH or depth > max_depth:
        return None
    label = f"[bold cyan]{m.type}[/] [white]{m.name}[/]"
    if m.value:
        label += f" [dim]= {str(m.value)[:70]}[/]"
    tree = Tree(label)
    for child in m.children[:max_children]:
        sub = render_tree(child, max_children, max_depth, depth + 1)
        if sub:
            tree.add(sub)
    if len(m.children) > max_children:
        tree.add(f"[dim]… ещё {len(m.children) - max_children}[/]")
    return tree


def cmd_analyze(args):
    scope = DigitalMicroscope()
    if args.input == "-" or (not args.input and not sys.stdin.isatty()):
        content = sys.stdin.read()
        name = "stdin"
    else:
        p = Path(args.input)
        if not p.exists():
            print(f"Файл не найден: {args.input}", file=sys.stderr)
            sys.exit(1)
        content = p
        name = p.name

    root = scope.analyze(content, filename=name, force_type=args.type)
    stats = scope.get_stats(root)

    if args.json:
        print(json.dumps({"stats": stats, "tree": root.to_dict()}, ensure_ascii=False, indent=2))
        return

    if args.mermaid:
        print(scope.to_mermaid(root))
        return

    if HAS_RICH:
        console.print(Panel(
            f"[bold]Образец:[/] {name}\n"
            f"[bold]Тип:[/] {root.metadata.get('detected_type')}\n"
            f"[bold]Молекул:[/] {stats['total_molecules']}\n"
            f"[bold]Глубина:[/] {stats['depth']}\n"
            f"[bold]Размер:[/] {root.metadata.get('size_bytes', '?')} байт",
            title="[bold]Микроскоп цифрового пространства[/]",
            border_style="cyan"
        ))
        tree = render_tree(root)
        if tree:
            console.print(tree)
    else:
        print(f"=== {name} | {root.metadata.get('detected_type')} | {stats['total_molecules']} молекул ===")
        def plain(m, ind=0):
            print("  " * ind + f"{m.type}: {m.name}" + (f" = {m.value[:50]}" if m.value else ""))
            for c in m.children[:15]:
                plain(c, ind + 1)
        plain(root)


def cmd_compare(args):
    scope = DigitalMicroscope()
    a = scope.analyze(Path(args.a))
    b = scope.analyze(Path(args.b))
    diff = scope.compare(a, b)
    print(json.dumps(diff, ensure_ascii=False, indent=2))


def cmd_serve(args):
    import uvicorn
    from microscope.web import app
    uvicorn.run(app, host=args.host, port=args.port)


def main():
    parser = argparse.ArgumentParser(
        prog="microscope",
        description="Микроскоп цифрового пространства — изучение цифровой ткани"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_an = sub.add_parser("analyze", help="Анализировать образец")
    p_an.add_argument("input", nargs="?", help="Файл или - для stdin")
    p_an.add_argument("-t", "--type", help="Принудительный тип")
    p_an.add_argument("-j", "--json", action="store_true")
    p_an.add_argument("--mermaid", action="store_true")
    p_an.set_defaults(func=cmd_analyze)

    p_cmp = sub.add_parser("compare", help="Сравнить два образца")
    p_cmp.add_argument("a")
    p_cmp.add_argument("b")
    p_cmp.set_defaults(func=cmd_compare)

    p_srv = sub.add_parser("serve", help="Запустить веб-интерфейс")
    p_srv.add_argument("--host", default="0.0.0.0")
    p_srv.add_argument("--port", type=int, default=8000)
    p_srv.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
