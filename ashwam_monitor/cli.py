import click
from pathlib import Path
import sys
from functools import wraps

from .io.loader import load_parser_outputs, load_journals_as_dict, load_gold_labels
from .io.writer import write_invariant_report, write_drift_report, write_canary_report, write_summary_report
from .invariants.runner import run_invariant_checks
from .metrics.comparator import run_drift_analysis
from .canary.runner import run_canary_evaluation
from .explainability.pm_view import generate_pm_view
from .exceptions import AshwamMonitorError, DataLoadError


def handle_errors(func):
    # decorator to catch errors and show friendly messages
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DataLoadError as e:
            click.echo(f"error loading file: {e}", err=True)
            sys.exit(1)
        except AshwamMonitorError as e:
            click.echo(f"error: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"unexpected error: {e}", err=True)
            sys.exit(1)
    return wrapper


@click.group()
@click.version_option(version="1.0.0", prog_name="ashwam-monitor")
def cli():
    """
    ashwam production monitoring tool
    
    detects model drift and unsafe behavior in journal parser outputs
    without requiring ground truth labels
    
    example: python -m ashwam_monitor run --data ./data --out ./out
    """
    pass


@cli.command()
@click.option("--data", "-d", type=click.Path(exists=True), required=True,
              help="data directory with journals and parser outputs")
@click.option("--out", "-o", type=click.Path(), default="./out",
              help="output directory for reports")
@click.option("--baseline", "-b", default="parser_outputs_day0.jsonl",
              help="baseline parser outputs file")
@click.option("--current", "-c", default="parser_outputs_day1.jsonl",
              help="current parser outputs to check")
@click.option("--verbose", "-v", is_flag=True, help="show debug info")
@click.option("--format", "-f", type=click.Choice(["json", "markdown"]), default="json",
              help="output format: json (default) or markdown (PM view)")
@click.option("--dry-run", is_flag=True, 
              help="preview mode: run all checks but don't write files")
@click.option("--log", is_flag=True,
              help="enable file logging to out/logs/")
@click.option("--store-history", is_flag=True,
              help="store run in SQLite database for trend analysis")
@handle_errors
def run(data, out, baseline, current, verbose, format, dry_run, log, store_history):
    """run complete monitoring suite"""
    from .logging_config import setup_logging, get_logger
    from .storage import RunHistoryDB
    
    data_path = Path(data)
    out_path = Path(out)

    # Setup logging
    log_dir = out_path / "logs" if log else None
    setup_logging(log_dir=log_dir, verbose=verbose)
    logger = get_logger()
    
    if dry_run:
        click.echo("=== DRY RUN MODE (no files will be written) ===\n")
        logger.info("Starting dry run")
    
    click.echo(f"running monitoring on {data_path}")
    logger.info(f"Data source: {data_path}")
    
    if not dry_run:
        click.echo(f"output to {out_path}")

    # load data
    journals = load_journals_as_dict(data_path / "journals.jsonl")
    baseline_outputs, base_errors = load_parser_outputs(data_path / baseline)
    current_outputs, curr_errors = load_parser_outputs(data_path / current)
    
    logger.info(f"Loaded {len(journals)} journals")
    logger.info(f"Baseline: {len(baseline_outputs)} outputs, {len(base_errors)} errors")
    logger.info(f"Current: {len(current_outputs)} outputs, {len(curr_errors)} errors")

    if verbose:
        click.echo(f"loaded {len(journals)} journals")
        click.echo(f"baseline: {len(baseline_outputs)} outputs, {len(base_errors)} errors")
        click.echo(f"current: {len(current_outputs)} outputs, {len(curr_errors)} errors")

    # run invariant checks on current
    click.echo("running invariant checks...")
    logger.info("Running invariant checks")
    invariant_report = run_invariant_checks(current_outputs, journals)
    logger.info(f"Invariants: hallucination={invariant_report.hallucination_rate:.1%}, contradiction={invariant_report.contradiction_rate:.1%}")

    # run drift analysis
    click.echo("running drift analysis...")
    logger.info("Running drift analysis")
    drift_report = run_drift_analysis(baseline_outputs, current_outputs, baseline, current)
    logger.info(f"Drift: {len(drift_report.alerts)} alerts")

    # run canary if gold labels exist - evaluate CURRENT outputs not baseline
    canary_path = data_path / "canary" / "gold.jsonl"
    canary_report = None
    if canary_path.exists():
        click.echo("running canary evaluation...")
        logger.info("Running canary evaluation")
        gold_labels, _ = load_gold_labels(canary_path)
        canary_ids = {g.journal_id for g in gold_labels}
        canary_outputs = [o for o in current_outputs if o.journal_id in canary_ids]
        canary_report = run_canary_evaluation(canary_outputs, gold_labels)
        logger.info(f"Canary: F1={canary_report.f1:.1%}, action={canary_report.action.value}")

    # write reports (skip if dry-run)
    if not dry_run:
        click.echo("writing reports...")
        write_invariant_report(invariant_report, out_path)
        write_drift_report(drift_report, out_path)
        if canary_report:
            write_canary_report(canary_report, out_path)
            write_summary_report(invariant_report, drift_report, canary_report, out_path)

        # generate PM view if markdown format requested
        if format == "markdown":
            pm_view = generate_pm_view(invariant_report, drift_report, canary_report)
            md_path = out_path / "dashboard.md"
            md_path.parent.mkdir(parents=True, exist_ok=True)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(pm_view)
            click.echo(f"Dashboard written to {md_path}")
        
        # Store in history database if requested
        if store_history:
            db = RunHistoryDB(out_path / "run_history.db")
            db.save_run(
                run_id=invariant_report.run_id,
                invariant_report=invariant_report,
                drift_report=drift_report,
                canary_report=canary_report,
                data_source=str(data_path)
            )
            click.echo(f"Run saved to history database: {out_path / 'run_history.db'}")
            logger.info(f"Run {invariant_report.run_id} saved to database")

    # print summary
    click.echo("\n=== SUMMARY ===")
    click.echo(f"hallucination rate: {invariant_report.hallucination_rate:.1%}")
    click.echo(f"contradiction rate: {invariant_report.contradiction_rate:.1%}")
    click.echo(f"alerts: {len(invariant_report.alerts)}")

    for alert in invariant_report.alerts[:3]:
        click.echo(f"  {alert}")
        logger.warning(alert)

    if canary_report:
        click.echo(f"\ncanary f1: {canary_report.f1:.1%}")
        click.echo(f"canary action: {canary_report.action.value}")

    if dry_run:
        click.echo("\n=== DRY RUN COMPLETE (no files written) ===")
    else:
        click.echo(f"\nreports written to {out_path}")


@cli.command()
@click.option("--outputs", "-o", type=click.Path(exists=True), required=True,
              help="parser outputs jsonl file")
@click.option("--journals", "-j", type=click.Path(exists=True), required=True,
              help="source journals jsonl file")
@click.option("--out", type=click.Path(), default="./out",
              help="output directory")
def invariants(outputs, journals, out):
    """run invariant checks only"""
    journals_dict = load_journals_as_dict(Path(journals))
    parser_outputs, _ = load_parser_outputs(Path(outputs))

    report = run_invariant_checks(parser_outputs, journals_dict)

    out_path = Path(out)
    write_invariant_report(report, out_path)

    click.echo(f"hallucination rate: {report.hallucination_rate:.1%}")
    click.echo(f"contradiction rate: {report.contradiction_rate:.1%}")
    click.echo(f"violations: {len(report.violations)}")
    click.echo(f"report written to {out_path / 'invariant_report.json'}")


@cli.command()
@click.option("--baseline", "-b", type=click.Path(exists=True), required=True,
              help="baseline parser outputs")
@click.option("--current", "-c", type=click.Path(exists=True), required=True,
              help="current parser outputs")
@click.option("--out", type=click.Path(), default="./out",
              help="output directory")
def drift(baseline, current, out):
    """compare drift between two output sets"""
    base_outputs, _ = load_parser_outputs(Path(baseline))
    curr_outputs, _ = load_parser_outputs(Path(current))

    report = run_drift_analysis(base_outputs, curr_outputs)

    out_path = Path(out)
    write_drift_report(report, out_path)

    for m in report.metrics:
        status = "⚠️" if m.status.value != "STABLE" else "✓"
        click.echo(f"{m.name}: {m.baseline_value} -> {m.current_value} {status}")

    click.echo(f"\nreport written to {out_path / 'drift_report.json'}")


@cli.command()
@click.option("--canary-dir", "-c", type=click.Path(exists=True), required=True,
              help="directory with canary journals and gold labels")
@click.option("--outputs", "-o", type=click.Path(exists=True), required=True,
              help="parser outputs to evaluate")
@click.option("--out", type=click.Path(), default="./out",
              help="output directory")
def canary(canary_dir, outputs, out):
    """run canary evaluation against gold labels"""
    canary_path = Path(canary_dir)
    gold_labels, _ = load_gold_labels(canary_path / "gold.jsonl")
    parser_outputs, _ = load_parser_outputs(Path(outputs))

    # filter to canary journals
    canary_ids = {g.journal_id for g in gold_labels}
    canary_outputs = [o for o in parser_outputs if o.journal_id in canary_ids]

    report = run_canary_evaluation(canary_outputs, gold_labels)

    out_path = Path(out)
    write_canary_report(report, out_path)

    click.echo(f"precision: {report.precision:.1%}")
    click.echo(f"recall: {report.recall:.1%}")
    click.echo(f"f1: {report.f1:.1%}")
    click.echo(f"action: {report.action.value}")
    click.echo(f"\nreport written to {out_path / 'canary_report.json'}")


@cli.command("review-queue")
@click.option("--invariant-report", "-i", type=click.Path(exists=True), required=True,
              help="invariant report json file")
@click.option("--limit", "-l", type=int, default=10,
              help="max items to show")
@handle_errors
def review_queue(invariant_report, limit):
    """show items that need human review based on invariant violations"""
    import json
    from .human_loop.queue import ReviewQueue, ReviewItem
    from .models.enums import AlertLevel
    from .config import config
    
    with open(invariant_report, encoding="utf-8") as f:
        report = json.load(f)
    
    queue = ReviewQueue()
    
    for v in report.get("violations", []):
        severity = AlertLevel.CRITICAL if v["severity"] == "critical" else AlertLevel.WARNING
        item = ReviewItem(
            id=f"{v['journal_id']}-{v['item_index']}",
            journal_id=v["journal_id"],
            violation_type=v["violation_type"],
            severity=severity,
            evidence_span=v.get("evidence_span", ""),
            details=v["details"],
            confidence=0.5
        )
        queue.add(item)
    
    # get priority batch
    batch = queue.get_daily_batch()
    critical = queue.get_critical_items()
    
    click.echo(f"\n=== REVIEW QUEUE ===")
    click.echo(f"total items: {len(queue.items)}")
    click.echo(f"critical items: {len(critical)}")
    click.echo(f"daily batch: {len(batch)}")
    
    click.echo(f"\n--- top {limit} items ---")
    for item in batch[:limit]:
        emoji = "🔴" if item.severity == AlertLevel.CRITICAL else "🟡"
        click.echo(f"{emoji} [{item.journal_id}] {item.violation_type}: {item.details[:50]}...")


@cli.command()
@click.option("--data", "-d", type=click.Path(exists=True), required=True,
              help="data directory with journals and parser outputs")
@click.option("--out", "-o", type=click.Path(), default="./out",
              help="output directory for reports")
@click.option("--baseline", "-b", default="parser_outputs_day0.jsonl",
              help="baseline parser outputs file")
@click.option("--current", "-c", default="parser_outputs_day1.jsonl",
              help="current parser outputs to check")
@handle_errors
def analyze(data, out, baseline, current):
    """
    Advanced analysis with wow-factor features:
    - Diff visualization
    - Auto-diagnosis of root causes
    - Simulated alert timeline
    - Confidence intervals
    - Human review sheet export
    """
    from .analytics import (
        generate_diff_visualization,
        generate_auto_diagnosis,
        generate_alert_timeline,
        generate_confidence_report,
        generate_human_review_sheet
    )
    import json
    
    data_path = Path(data)
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    
    click.echo("=== ADVANCED ANALYSIS ===\n")
    
    # load data
    journals = load_journals_as_dict(data_path / "journals.jsonl")
    baseline_outputs, _ = load_parser_outputs(data_path / baseline)
    current_outputs, _ = load_parser_outputs(data_path / current)
    
    # run checks
    invariant_report = run_invariant_checks(current_outputs, journals)
    drift_report = run_drift_analysis(baseline_outputs, current_outputs, baseline, current)
    
    # canary if exists
    canary_path = data_path / "canary" / "gold.jsonl"
    canary_report = None
    if canary_path.exists():
        gold_labels, _ = load_gold_labels(canary_path)
        canary_ids = {g.journal_id for g in gold_labels}
        canary_outputs = [o for o in current_outputs if o.journal_id in canary_ids]
        canary_report = run_canary_evaluation(canary_outputs, gold_labels)
    
    # 1. Diff Visualization
    diff_viz = generate_diff_visualization(drift_report)
    click.echo(diff_viz)
    
    # 2. Auto-Diagnosis
    click.echo("=== AUTO-DIAGNOSIS ===")
    diagnosis = generate_auto_diagnosis(invariant_report)
    if diagnosis["patterns_detected"]:
        click.echo(f"\n🔍 Patterns detected: {len(diagnosis['patterns_detected'])}")
        for pattern in diagnosis["patterns_detected"]:
            click.echo(f"  • {pattern['type']}: {pattern['description']}")
        click.echo(f"\n💡 Likely causes:")
        for cause in diagnosis["likely_causes"]:
            click.echo(f"  → {cause}")
        click.echo(f"\n🔧 Recommended actions:")
        for action in diagnosis["recommended_actions"]:
            click.echo(f"  ✓ {action}")
    else:
        click.echo("  No systematic patterns detected.")
    
    # 3. Confidence Intervals
    click.echo("\n=== CONFIDENCE INTERVALS (95%) ===")
    confidence = generate_confidence_report(invariant_report)
    for metric_name, metric_data in confidence["metrics"].items():
        click.echo(f"  {metric_name}: {metric_data['display']}")
    click.echo(f"\n📊 Interpretation: {confidence['interpretation']}")
    
    # 4. Alert Timeline
    click.echo("\n=== SIMULATED ALERT TIMELINE ===")
    timeline = generate_alert_timeline(invariant_report, drift_report, canary_report)
    for day in timeline:
        click.echo(f"  Day {day['day']} ({day['date']}): {day['icon']} {day['status']}")
        for event in day["events"][:2]:  # limit events shown
            click.echo(f"       └─ {event}")
    
    # 5. Generate Human Review Sheet
    review_sheet = generate_human_review_sheet(invariant_report, journals)
    review_path = out_path / "human_review_sheet.md"
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(review_sheet)
    click.echo(f"\n✅ Human review sheet exported to: {review_path}")
    
    # Save analysis to JSON
    analysis_output = {
        "diff_visualization": diff_viz,
        "diagnosis": diagnosis,
        "confidence_intervals": confidence,
        "timeline": timeline
    }
    analysis_path = out_path / "advanced_analysis.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis_output, f, indent=2, default=str)
    click.echo(f"✅ Full analysis saved to: {analysis_path}")


if __name__ == "__main__":
    cli()

