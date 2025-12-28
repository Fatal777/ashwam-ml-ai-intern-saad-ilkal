import click
from pathlib import Path


@click.group()
@click.version_option(version="1.0.0", prog_name="ashwam-monitor")
def cli():
    """ashwam production monitoring - detect drift and issues in parser outputs"""
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
def run(data, out, baseline, current, verbose):
    """run complete monitoring suite"""
    # will implement in later phases
    click.echo(f"running monitoring on {data}")
    click.echo(f"baseline: {baseline}, current: {current}")
    click.echo(f"output to: {out}")


@cli.command()
@click.option("--outputs", "-o", type=click.Path(exists=True), required=True,
              help="parser outputs jsonl file")
@click.option("--journals", "-j", type=click.Path(exists=True), required=True,
              help="source journals jsonl file")
def invariants(outputs, journals):
    """run invariant checks only"""
    click.echo(f"checking invariants: {outputs} against {journals}")


@cli.command()
@click.option("--baseline", "-b", type=click.Path(exists=True), required=True,
              help="baseline parser outputs")
@click.option("--current", "-c", type=click.Path(exists=True), required=True,
              help="current parser outputs")
def drift(baseline, current):
    """compare drift between two output sets"""
    click.echo(f"comparing drift: {baseline} vs {current}")


@cli.command()
@click.option("--canary-dir", "-c", type=click.Path(exists=True), required=True,
              help="directory with canary journals and gold labels")
@click.option("--outputs", "-o", type=click.Path(exists=True), required=True,
              help="parser outputs to evaluate")
def canary(canary_dir, outputs):
    """run canary evaluation against gold labels"""
    click.echo(f"canary eval: {outputs} against {canary_dir}")


if __name__ == "__main__":
    cli()
