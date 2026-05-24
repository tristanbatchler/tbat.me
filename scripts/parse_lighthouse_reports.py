#!/usr/bin/env python3
"""Extract structured summaries from Lighthouse JSON reports.

Usage:
  python3 scripts/parse_lighthouse_reports.py /tmp/lighthouse-*.json \
      --json-out /tmp/lighthouse-summary.json \
      --md-out /tmp/lighthouse-summary.md
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from dataclasses import dataclass
from typing import Any, cast


CATEGORY_ORDER = ["performance", "accessibility", "best-practices", "seo", "agentic-browsing"]

METRIC_AUDITS = {
    "first-contentful-paint": "FCP",
    "largest-contentful-paint": "LCP",
    "speed-index": "Speed Index",
    "total-blocking-time": "TBT",
    "cumulative-layout-shift": "CLS",
    "interactive": "TTI",
}

INSIGHT_AUDITS = [
    "image-delivery-insight",
    "render-blocking-insight",
    "cache-insight",
    "document-latency-insight",
    "font-display-insight",
    "lcp-discovery-insight",
    "layout-shifts",
    "cls-culprits-insight",
    "network-dependency-tree-insight",
    "bf-cache",
]

DETAIL_PROJECTION_KEYS = [
    "url",
    "totalBytes",
    "wastedBytes",
    "wastedMs",
    "score",
    "reason",
    "cacheLifetimeMs",
]


@dataclass
class ReportSummary:
    slug: str
    file: str
    url: str
    lighthouse_version: str
    fetch_time: str
    category_scores: dict[str, int]
    metrics: dict[str, dict[str, Any]]
    perf_weighted_contributors: list[dict[str, Any]]
    savings_audits: list[dict[str, Any]]
    insight_findings: list[dict[str, Any]]
    failed_nonperf: dict[str, list[dict[str, Any]]]


def score_to_100(score: Any) -> int:
    if score is None:
        return -1
    return int(round(float(score) * 100))


def float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        value_dict = cast(dict[Any, Any], value)
        out: dict[str, Any] = {}
        for k, v in value_dict.items():
            out[str(k)] = v
        return out
    return {}


def compact_projection(item: dict[str, Any]) -> dict[str, Any]:
    projection: dict[str, Any] = {}
    for key in DETAIL_PROJECTION_KEYS:
        if key in item:
            projection[key] = item[key]

    node = ensure_dict(item.get("node"))
    if node:
        projection["nodeSelector"] = node.get("selector")
        projection["nodeLabel"] = node.get("nodeLabel")
        projection["nodeSnippet"] = node.get("snippet")
    return projection


def readable_slug(path: str) -> str:
    name = os.path.basename(path)
    if name.startswith("lighthouse-"):
        name = name[len("lighthouse-") :]
    if name.endswith(".json"):
        name = name[:-5]
    return name


def get_metric(audits: dict[str, Any], audit_id: str, label: str) -> dict[str, Any]:
    audit = audits.get(audit_id, {})
    return {
        "id": audit_id,
        "label": label,
        "score": audit.get("score"),
        "score_100": score_to_100(audit.get("score")),
        "numericValue": audit.get("numericValue"),
        "displayValue": audit.get("displayValue"),
    }


def extract_weighted_perf_contributors(lhr: dict[str, Any]) -> list[dict[str, Any]]:
    audits = lhr.get("audits", {})
    refs = lhr.get("categories", {}).get("performance", {}).get("auditRefs", [])
    out: list[dict[str, Any]] = []

    for ref in refs:
        aid = ref.get("id")
        weight = ref.get("weight", 0)
        if weight <= 0:
            continue

        audit = audits.get(aid, {})
        score = audit.get("score")
        mode = audit.get("scoreDisplayMode")
        if mode in {"notApplicable", "informative", "manual", "error"}:
            continue
        if score is None or score >= 1:
            continue

        out.append(
            {
                "id": aid,
                "title": audit.get("title", aid),
                "weight": weight,
                "score": score,
                "score_100": score_to_100(score),
                "displayValue": audit.get("displayValue"),
                "numericValue": audit.get("numericValue"),
            }
        )

    out.sort(key=lambda x: (-x.get("weight", 0), x.get("score_100", 101)))
    return out


def extract_savings_audits(lhr: dict[str, Any]) -> list[dict[str, Any]]:
    audits = lhr.get("audits", {})
    out: list[dict[str, Any]] = []

    for aid, audit in audits.items():
        details = ensure_dict(audit.get("details"))
        savings_ms = float_or_none(details.get("overallSavingsMs"))
        savings_b = float_or_none(details.get("overallSavingsBytes"))
        if not savings_ms and not savings_b:
            continue

        mode = audit.get("scoreDisplayMode")
        if mode in {"notApplicable", "informative", "manual", "error"}:
            continue

        first_item = None
        items_value = details.get("items")
        if isinstance(items_value, list) and items_value and isinstance(items_value[0], dict):
            first_item = compact_projection(ensure_dict(items_value[0]))

        out.append(
            {
                "id": aid,
                "title": audit.get("title", aid),
                "score": audit.get("score"),
                "score_100": score_to_100(audit.get("score")),
                "displayValue": audit.get("displayValue"),
                "overallSavingsMs": savings_ms,
                "overallSavingsBytes": savings_b,
                "firstItem": first_item,
            }
        )

    out.sort(key=lambda x: (-(x.get("overallSavingsMs") or 0), -(x.get("overallSavingsBytes") or 0)))
    return out


def extract_insight_findings(lhr: dict[str, Any]) -> list[dict[str, Any]]:
    audits = lhr.get("audits", {})
    out: list[dict[str, Any]] = []

    for aid in INSIGHT_AUDITS:
        audit = audits.get(aid)
        if not audit:
            continue

        score = audit.get("score")
        if score is None or score >= 1:
            continue

        details = ensure_dict(audit.get("details"))
        item_sample = None
        checklist_values = None

        items_value = details.get("items")
        if isinstance(items_value, list) and items_value:
            items_list = cast(list[Any], items_value)
            first_value: Any = items_list[0]
            if isinstance(first_value, dict):
                item_sample = compact_projection(ensure_dict(first_value))
        elif isinstance(items_value, dict):
            checklist_values = {}
            for key, val in ensure_dict(items_value).items():
                val_dict = ensure_dict(val)
                if "value" in val_dict:
                    checklist_values[str(key)] = val_dict.get("value")

        out.append(
            {
                "id": aid,
                "title": audit.get("title", aid),
                "score": score,
                "score_100": score_to_100(score),
                "scoreDisplayMode": audit.get("scoreDisplayMode"),
                "displayValue": audit.get("displayValue"),
                "overallSavingsMs": details.get("overallSavingsMs"),
                "overallSavingsBytes": details.get("overallSavingsBytes"),
                "itemSample": item_sample,
                "checklistValues": checklist_values,
            }
        )

    out.sort(key=lambda x: (x.get("score_100", 101), -(x.get("overallSavingsMs") or 0)))
    return out


def extract_failed_nonperf(lhr: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    audits = lhr.get("audits", {})
    categories = lhr.get("categories", {})
    result: dict[str, list[dict[str, Any]]] = {}

    for cat in ["accessibility", "best-practices", "seo", "agentic-browsing"]:
        refs = categories.get(cat, {}).get("auditRefs", [])
        failures: list[dict[str, Any]] = []
        for ref in refs:
            aid = ref.get("id")
            weight = ref.get("weight", 0)
            audit = audits.get(aid, {})
            score = audit.get("score")
            mode = audit.get("scoreDisplayMode")

            if weight <= 0:
                continue
            if mode in {"notApplicable", "informative", "manual"}:
                continue
            if score is None or score >= 1:
                continue

            failures.append(
                {
                    "id": aid,
                    "title": audit.get("title", aid),
                    "weight": weight,
                    "score": score,
                    "score_100": score_to_100(score),
                    "displayValue": audit.get("displayValue"),
                    "description": audit.get("description"),
                    "explanation": audit.get("explanation"),
                }
            )

        failures.sort(key=lambda x: (x.get("score_100", 101), -x.get("weight", 0)))
        result[cat] = failures

    return result


def summarize_report(path: str) -> ReportSummary:
    with open(path, "r", encoding="utf-8") as f:
        lhr = json.load(f)

    audits = lhr.get("audits", {})
    categories = lhr.get("categories", {})

    category_scores: dict[str, int] = {}
    for cat in CATEGORY_ORDER:
        if cat in categories:
            category_scores[cat] = score_to_100(categories[cat].get("score"))

    metrics = {
        aid: get_metric(audits, aid, label)
        for aid, label in METRIC_AUDITS.items()
        if aid in audits
    }

    return ReportSummary(
        slug=readable_slug(path),
        file=path,
        url=lhr.get("finalDisplayedUrl") or lhr.get("finalUrl") or lhr.get("requestedUrl") or "",
        lighthouse_version=lhr.get("lighthouseVersion", ""),
        fetch_time=lhr.get("fetchTime", ""),
        category_scores=category_scores,
        metrics=metrics,
        perf_weighted_contributors=extract_weighted_perf_contributors(lhr),
        savings_audits=extract_savings_audits(lhr),
        insight_findings=extract_insight_findings(lhr),
        failed_nonperf=extract_failed_nonperf(lhr),
    )


def render_markdown(summaries: list[ReportSummary]) -> str:
    lines: list[str] = []
    lines.append("# Lighthouse Baseline Summary")
    lines.append("")
    lines.append("This summary is derived from Lighthouse JSON output and focuses on highest-impact keys:")
    lines.append("- categories.*.score")
    lines.append("- audits.[CWV metric IDs].numericValue/displayValue")
    lines.append("- categories.performance.auditRefs for weighted contributors")
    lines.append("- audits.*.details.overallSavingsMs/Bytes for concrete opportunities")
    lines.append("- v13 insight audits for root-cause diagnostics")
    lines.append("- weighted failing audits in accessibility, best-practices, SEO, and agentic-browsing")
    lines.append("")

    lines.append("## Category Scores")
    lines.append("")
    lines.append("| Page | Performance | Accessibility | Best Practices | SEO | Agentic |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for s in summaries:
        lines.append(
            "| {page} | {p} | {a11y} | {bp} | {seo} | {agentic} |".format(
                page=s.slug,
                p=s.category_scores.get("performance", "n/a"),
                a11y=s.category_scores.get("accessibility", "n/a"),
                bp=s.category_scores.get("best-practices", "n/a"),
                seo=s.category_scores.get("seo", "n/a"),
                agentic=s.category_scores.get("agentic-browsing", "n/a"),
            )
        )

    for s in summaries:
        lines.append("")
        lines.append(f"## {s.slug}")
        lines.append("")
        lines.append(f"- URL: {s.url}")
        lines.append(f"- Report file: {s.file}")
        lines.append(f"- Lighthouse version: {s.lighthouse_version}")
        lines.append(f"- Fetch time: {s.fetch_time}")

        lines.append("")
        lines.append("### Key Metrics")
        lines.append("")
        lines.append("| Metric | Value | Score |")
        lines.append("|---|---|---:|")
        for m in s.metrics.values():
            lines.append(f"| {m['label']} | {m.get('displayValue') or m.get('numericValue')} | {m.get('score_100')} |")

        lines.append("")
        lines.append("### Performance Score Contributors (Weighted)")
        lines.append("")
        if not s.perf_weighted_contributors:
            lines.append("- None")
        else:
            for o in s.perf_weighted_contributors[:10]:
                lines.append(
                    "- {title} ({id}): weight={weight}, score={score}, display={display}".format(
                        title=o.get("title"),
                        id=o.get("id"),
                        weight=o.get("weight"),
                        score=o.get("score_100"),
                        display=o.get("displayValue") or "n/a",
                    )
                )

        lines.append("")
        lines.append("### Savings Opportunities (All Audits)")
        lines.append("")
        if not s.savings_audits:
            lines.append("- None")
        else:
            for o in s.savings_audits[:10]:
                sms = o.get("overallSavingsMs")
                sbytes = o.get("overallSavingsBytes")
                lines.append(
                    "- {title} ({id}): score={score}, savings_ms={sms}, savings_bytes={sbytes}, display={display}".format(
                        title=o.get("title"),
                        id=o.get("id"),
                        score=o.get("score_100"),
                        sms=f"{sms:.0f}" if isinstance(sms, (int, float)) else "n/a",
                        sbytes=f"{sbytes:.0f}" if isinstance(sbytes, (int, float)) else "n/a",
                        display=o.get("displayValue") or "n/a",
                    )
                )
                if o.get("firstItem"):
                    lines.append(f"  - sample={o['firstItem']}")

        lines.append("")
        lines.append("### Key Insight Audits")
        lines.append("")
        if not s.insight_findings:
            lines.append("- None")
        else:
            for i in s.insight_findings[:10]:
                lines.append(
                    "- {title} ({id}): score={score}, display={display}".format(
                        title=i.get("title"),
                        id=i.get("id"),
                        score=i.get("score_100"),
                        display=i.get("displayValue") or "n/a",
                    )
                )
                if i.get("itemSample"):
                    lines.append(f"  - sample={i['itemSample']}")
                if i.get("checklistValues"):
                    lines.append(f"  - checklist={i['checklistValues']}")

        lines.append("")
        lines.append("### Failed Weighted Audits (Non-Performance)")
        lines.append("")
        for cat, failures in s.failed_nonperf.items():
            lines.append(f"- {cat}:")
            if not failures:
                lines.append("  - None")
                continue
            for f in failures[:10]:
                lines.append(
                    "  - {title} ({id}): score={score}, weight={weight}, display={display}".format(
                        title=f.get("title"),
                        id=f.get("id"),
                        score=f.get("score_100"),
                        weight=f.get("weight"),
                        display=f.get("displayValue") or "n/a",
                    )
                )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse Lighthouse JSON reports into concise summaries.")
    parser.add_argument("inputs", nargs="+", help="Input files or globs (for example /tmp/lighthouse-*.json)")
    parser.add_argument("--json-out", required=True, help="Path to write machine-readable extracted summary JSON")
    parser.add_argument("--md-out", required=True, help="Path to write human-readable markdown summary")
    return parser.parse_args()


def expand_inputs(inputs: list[str]) -> list[str]:
    files: list[str] = []
    for inp in inputs:
        matches = sorted(glob.glob(inp))
        if matches:
            files.extend(matches)
        elif os.path.exists(inp):
            files.append(inp)

    deduped = sorted(dict.fromkeys(files))
    deduped = [
        path
        for path in deduped
        if not os.path.basename(path).startswith("lighthouse-summary")
    ]
    if not deduped:
        raise SystemExit("No input files found")
    return deduped


def main() -> None:
    args = parse_args()
    files = expand_inputs(args.inputs)
    summaries = [summarize_report(path) for path in files]

    json_payload = {
        "source": "lighthouse-json",
        "reports": [s.__dict__ for s in summaries],
    }

    os.makedirs(os.path.dirname(args.json_out), exist_ok=True)
    os.makedirs(os.path.dirname(args.md_out), exist_ok=True)

    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2)

    with open(args.md_out, "w", encoding="utf-8") as f:
        f.write(render_markdown(summaries))

    print(f"Wrote {args.json_out}")
    print(f"Wrote {args.md_out}")


if __name__ == "__main__":
    main()