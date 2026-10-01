"""Readable report folders and a history page ordered newest first."""
import html
import json
import os
import tempfile
from datetime import timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from .core import timestamp

IST = timezone(timedelta(hours=5, minutes=30), name="IST")
KINDS = {"screen", "demo", "evidence"}


def report_folder_name(report, kind):
    if kind not in KINDS:
        raise ValueError("Unsupported report kind")
    generated = timestamp(report["generated_at"]).astimezone(IST)
    return generated.strftime("%Y-%m-%d_%H-%M-%S_IST_") + kind


def create_report_directory(root, report, kind, *, allow_collision=False):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    base = report_folder_name(report, kind)
    for sequence in range(1, 10000):
        name = base if sequence == 1 else f"{base}_{sequence:04d}"
        directory = root / name
        try:
            directory.mkdir(exist_ok=False)
            return directory
        except FileExistsError:
            if not allow_collision:
                raise
            if report.get("id"):
                try:
                    saved = json.loads((directory / "research.json").read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    saved = {}
                if saved.get("id") == report["id"]:
                    raise
    raise FileExistsError("Too many reports with the same generation timestamp")


def refresh_report_index(root):
    root = Path(root)
    rows = []
    for directory in root.iterdir():
        if not directory.is_dir() or directory.is_symlink() or not (directory / "index.html").is_file():
            continue
        try:
            report = json.loads((directory / "research.json").read_text(encoding="utf-8"))
            generated = timestamp(report["generated_at"])
            mode = str(report.get("mode", "research"))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            continue
        rows.append((generated, directory.name, mode))
    rows.sort(key=lambda row: (row[0], row[1]), reverse=True)
    links = []
    for position, (generated, name, mode) in enumerate(rows):
        label = generated.astimezone(IST).strftime("%d %b %Y · %I:%M:%S %p IST")
        links.append(f'<li><a href="{quote(name, safe="")}/index.html">'
                     f'{html.escape(label)}{" · Latest" if position == 0 else ""}</a>'
                     f'<small>{html.escape(mode)}<br>{html.escape(name)}</small></li>')
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'">
<title>Research report history</title><style>
body{background:#0d1421;color:#e7edf7;font:16px/1.6 system-ui;margin:0;padding:32px}
main{max-width:900px;margin:auto}a{color:#9cdecf;text-decoration:none}small{display:block;color:#a6b5c9;overflow-wrap:anywhere}
ul{list-style:none;padding:0}li{padding:18px;margin:12px 0;background:#172132;border:1px solid #2c3a50;border-radius:12px}
</style></head><body><main><h1>Research report history</h1>
<p>Newest report first. All dates and times are in India Standard Time (IST).</p><ul>'''
    page += "".join(links) + "</ul></main></body></html>"
    # Replacing only the generated history page cannot overwrite a saved report.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root,
                                         prefix=".history-", suffix=".tmp", delete=False) as target:
            temporary = Path(target.name)
            target.write(page)
        os.replace(temporary, root / "index.html")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return root / "index.html"
