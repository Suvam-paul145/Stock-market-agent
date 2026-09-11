import argparse
import json
import os
import sys
from pathlib import Path

from .core import Store, load_config
from .research import collect, export


def main():
    parser = argparse.ArgumentParser(description="Local US-stock research collection; no trading or paid AI calls")
    parser.add_argument("command", choices=["doctor", "demo", "collect"])
    parser.add_argument("--config", default="config.example.json")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output", default="reports")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
    except (OSError, ValueError, TypeError, AttributeError):
        parser.error("Invalid or unreadable configuration; compare with config.example.json")
    if args.command == "doctor":
        print(json.dumps(dict(python=sys.version.split()[0], watchlist=config["watchlist"], horizon=config["horizon"],
                              credentials={name: bool(os.getenv(name)) for name in
                                           ("SEC_USER_AGENT", "APCA_API_KEY_ID", "APCA_API_SECRET_KEY")},
                              model_api="disabled", broker_execution="not implemented", monitoring="not running"), indent=2))
        return 0
    demo = args.command == "demo"
    store = Store(Path(args.data_dir) / ("demo.sqlite3" if demo else "research.sqlite3"))
    try:
        report = collect(config, store, demo=demo)
        directory = export(report, args.output)
    finally:
        store.close()
    print(f"Report: {directory.resolve()}")
    print(f"Mode: {report['mode']}. Requests: {report['request_count']}. Forecasts disabled.")
    degraded = any(p["status"] in ("error", "not_configured") for s in report["symbols"] for p in s["providers"].values())
    if degraded:
        print("Collection incomplete. See provider statuses in the report.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
