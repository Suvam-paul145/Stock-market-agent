"""Rename existing generated reports from their original timestamps; no network calls."""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stock_agent.report_paths import refresh_report_index, report_folder_name  # noqa: E402


def hashes(directory):
    result = {}
    for item in directory.rglob("*"):
        if item.is_symlink():
            raise ValueError("Report contains a symlink; migration stopped")
        if item.is_file():
            result[str(item.relative_to(directory))] = hashlib.sha256(item.read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Rename; default is a preview")
    args = parser.parse_args()
    root = (Path(__file__).resolve().parents[1] / "reports").resolve(strict=True)
    planned, skipped = [], []
    occupied = {p.name for p in root.iterdir()}
    for source in sorted(root.iterdir()):
        if not source.is_dir() or source.is_symlink():
            continue
        if not re.fullmatch(r"(?:screen-)?[a-f0-9-]{32,36}", source.name):
            continue
        if source.resolve().parent != root:
            raise ValueError("Report directory outside reports root")
        try:
            report = json.loads((source / "research.json").read_text(encoding="utf-8"))
            kind = "screen" if "boards" in report else "demo" if report.get("mode") == "synthetic_demo" else "evidence"
            base = report_folder_name(report, kind)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            skipped.append(source.name)
            continue
        name, sequence = base, 1
        while name in occupied:
            sequence += 1
            name = f"{base}_{sequence:04d}"
        occupied.add(name)
        target = root / name
        # Before any move, prove the resolved source and destination stay inside reports.
        if target.resolve().parent != root or target.exists():
            raise ValueError("Unsafe or occupied report destination")
        planned.append((source, target, hashes(source)))
    print(json.dumps({"apply": args.apply, "renames": [{"from": s.name, "to": t.name} for s, t, _ in planned],
                      "skipped": skipped}, indent=2))
    if not args.apply:
        return
    manifest = root / "folder-renames.json"
    history = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else []
    for source, target, before in planned:
        source.rename(target)
        if hashes(target) != before:
            raise ValueError("Report content changed during rename; inspection required")
        history.append({"from": source.name, "to": target.name, "renamed_at": datetime.now(timezone.utc).isoformat(),
                        "files_verified": len(before)})
        # Record each completed move so partial progress remains recoverable.
        manifest.write_text(json.dumps(history, indent=2), encoding="utf-8")
    refresh_report_index(root)
    print(f"Renamed {len(planned)} reports; file hashes verified. History: {root / 'index.html'}")


if __name__ == "__main__":
    main()
