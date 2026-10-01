import argparse
import json
from pathlib import Path

from .config import load_screen_config
from .pipeline import run_screen
from .report import export_screen


def main(argv=None):
    parser = argparse.ArgumentParser(description="On-demand, multi-horizon US-stock research screening")
    parser.add_argument("--config", default="screening.example.json")
    parser.add_argument("--output", default="reports")
    parser.add_argument("--no-filings", action="store_true", help="Skip optional SEC metadata enrichment")
    args = parser.parse_args(argv)
    try:
        config = load_screen_config(args.config)
        report, inputs = run_screen(config, include_filings=not args.no_filings)
        directory = export_screen(report, inputs, args.output)
    except (OSError, ValueError, TypeError, KeyError):
        print("Screen failed: check setup, screening configuration and writable output path. No secrets printed.")
        return 2
    print(f"Report: {(directory / 'index.html').resolve()}")
    print(f"Report history (newest first): {(Path(args.output) / 'index.html').resolve()}")
    print(json.dumps({k: dict(status=b["status"], count=len(b["candidates"]), coverage=b["coverage"])
                      for k, b in report["boards"].items()}, indent=2))
    print("Research only. Ranking scores are not probabilities. No orders placed.")
    return 2 if any(b["status"] == "unavailable" for b in report["boards"].values()) else 0
