import html
import json
from stock_agent.report_paths import create_report_directory, refresh_report_index


def render(report):
    def esc(value):
        return html.escape(str(value), quote=True)
    board_html = []
    for key in ("short_term", "one_month", "six_months", "today"):
        board = report["boards"][key]
        cards = []
        for row in board["candidates"]:
            metrics = row["metrics"]
            displays = []
            for name, value in metrics.items():
                if name.startswith(("return_", "excess_", "trend_")) or name in ("volatility", "drawdown", "session_change"):
                    displays.append(f"<span>{esc(name.replace('_', ' '))}<b>{value:+.2%}</b></span>")
            if "volume_fraction" in metrics:
                displays.append(f"<span>Volume / prior full-day average<b>{metrics['volume_fraction']:.2f}×</b></span>")
            filing = report["filings"].get(row["symbol"], {})
            links = "".join(f'<li><a href="{esc(f["url"])}" target="_blank" rel="noopener noreferrer">{esc(f["form"])} · {esc(f["filed_at"])}</a></li>' for f in filing.get("filings", []))
            cards.append(f'''<article><div class="cardtop"><h3><small>#{row['rank']}</small> {esc(row['symbol'])}</h3>
                <span class="score">{row['score']:.1f}<small>relative score / 100</small></span></div>
                <p class="muted">{esc(row['sector'])} · ${metrics['price']:.2f} · {esc(board['as_of_session'])}</p>
                <p>{esc(row['thesis'])}</p><div class="metrics">{''.join(displays)}</div>
                <p class="muted">{esc(row['invalidation'])}</p>
                <details><summary>Evidence and missing checks</summary><ul>{links or '<li>SEC metadata unavailable or not collected.</li>'}
                {''.join('<li>'+esc(g)+'</li>' for g in row['missing_evidence'])}</ul></details></article>''')
        exclusions = "".join(f"<li><b>{esc(s)}</b>: {esc(reason)}</li>" for s, reason in board["exclusions"].items())
        board_html.append(f'''<section id="{key}"><h2>{esc(board['label'])}</h2>
            <p>{esc(board['reason'])}.</p><p class="muted">{board['coverage']:.0%} data coverage · {len(board['candidates'])} of 5 slots filled · {esc(board['price_basis'])}</p>
            <div class="cards">{''.join(cards) or '<article>No eligible list available. Review coverage and provider status below.</article>'}</div>
            <details><summary>Excluded symbols ({len(board['exclusions'])})</summary><ul>{exclusions}</ul></details></section>''')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
    <title>Stock research · four horizons</title><style>
    :root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:#0d1421;color:#e7edf7;font:16px/1.6 system-ui,sans-serif}}
    main{{max-width:1180px;margin:auto;padding:40px 24px}}h1{{font-size:clamp(28px,4vw,46px);line-height:1.2;margin:10px 0}}h2{{margin:42px 0 4px}}h3{{font-size:25px;margin:0}}small,.muted{{color:#a6b5c9}}
    .eyebrow{{color:#7bd5c2;letter-spacing:.12em;text-transform:uppercase;font-size:12px}}.notice{{border-left:3px solid #e5b56d;padding:14px 20px;background:#242335;border-radius:8px;margin:24px 0}}
    nav{{display:flex;gap:10px;flex-wrap:wrap}}a{{color:#9cdecf}}nav a{{text-decoration:none;border:1px solid #384458;padding:8px 15px;border-radius:30px}}
    .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,330px),1fr));gap:16px;margin:20px 0}}article{{background:#172132;border:1px solid #2c3a50;padding:22px;border-radius:14px}}
    .cardtop{{display:flex;justify-content:space-between;align-items:center;gap:12px}}h3 small{{font-size:15px}}.score{{font-size:25px;color:#8be0c8;text-align:right}}.score small{{display:block;font-size:10px}}
    .metrics{{display:grid;grid-template-columns:1fr 1fr;gap:12px;border-top:1px solid #334055;padding-top:14px}}.metrics span{{font-size:12px;color:#a6b5c9}}.metrics b{{display:block;font-size:17px;color:#e7edf7}}details{{margin-top:18px}}summary{{cursor:pointer;color:#a6dacc}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}footer{{margin-top:35px;border-top:1px solid #344156;padding-top:20px}}
    </style></head><body><main><div class="eyebrow">Private research workbench · {esc(report['strategy_version'])}</div>
    <h1>One universe. Four perspectives.</h1><p class="muted">{esc(report['universe']['universe_name'])}<br>
    Generated {esc(report['generated_at'])} · Refresh after {esc(report['expires_at'])}</p>
    <div class="notice"><b>Research shortlists, not validated trade recommendations.</b> Scores compare eligible stocks within this universe.
    News, earnings and fundamentals still need review. This saved report does not update automatically.</div>
    <nav><a href="#short_term">1–7 days</a><a href="#one_month">1 month</a><a href="#six_months">6 months</a><a href="#today">Session leaders</a></nav>
    {''.join(board_html)}<footer><details><summary>Provider health, methodology and run details</summary>
    <pre>{esc(json.dumps({k: report[k] for k in ('providers','context','evaluation','assumptions','limitations','request_count')}, indent=2))}</pre></details>
    <p><a href="research.json">Structured report</a> · <a href="research.md">Readable report</a> · <a href="evidence.json">Saved public inputs</a></p></footer></main></body></html>'''


def export_screen(report, inputs, output):
    directory = create_report_directory(output, report, "screen", allow_collision=True)
    text = ["# Multi-horizon stock research", "", f"Generated: {report['generated_at']}",
            "", "Research shortlists only; strategy has not been validated. Scores are not probabilities.",
            "", f"Universe: {report['universe']['universe_name']}", ""]
    for board in report["boards"].values():
        text.extend(["## " + board["label"], "", board["reason"], "",
                     f"Coverage: {board['coverage']:.0%}. Session: {board['as_of_session']}", ""])
        for row in board["candidates"]:
            text.extend([f"### {row['rank']}. {row['symbol']} — score {row['score']}", "", row["thesis"], "",
                         "Metrics: " + json.dumps(row["metrics"], sort_keys=True), "", row["invalidation"], ""])
    text.extend(["## Limitations", "", *["- " + gap for gap in report["limitations"]], ""])
    for name, value in (("research.json", report), ("evidence.json", inputs)):
        (directory / name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    (directory / "research.md").write_text("\n".join(text), encoding="utf-8")
    (directory / "index.html").write_text(render(report), encoding="utf-8")
    refresh_report_index(output)
    return directory
