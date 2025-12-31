from typing import List
from datetime import datetime
import uuid

from ..models.inputs import ParserOutput, ParserItem
from ..models.outputs import DriftReport, DriftMetric
from ..models.enums import DriftStatus
from ..config import config

from .statistical import jensen_shannon_divergence, ks_test
from .extractors import (
    compute_uncertainty_rate,
    compute_extraction_volume,
    compute_domain_distribution,
    compute_arousal_distribution,
    compute_intensity_distribution
)


def get_all_items(outputs: List[ParserOutput]) -> List[ParserItem]:
    return [item for o in outputs for item in o.items]


def determine_status(js_div: float, thresholds) -> DriftStatus:
    if js_div >= thresholds.js_breakage:
        return DriftStatus.BREAKAGE
    elif js_div >= thresholds.js_drift:
        return DriftStatus.DRIFT
    return DriftStatus.STABLE


def compare_distributions(
    baseline_dist: dict,
    current_dist: dict,
    name: str,
    thresholds
) -> DriftMetric:
    """
    compare two distributions and return drift metric
    """
    # get all keys
    all_keys = sorted(set(baseline_dist.keys()) | set(current_dist.keys()))

    if not all_keys:
        return DriftMetric(
            name=name,
            baseline_value=0,
            current_value=0,
            change_pct=0,
            js_divergence=0,
            status=DriftStatus.STABLE
        )

    # build arrays
    baseline_arr = [baseline_dist.get(k, 0) for k in all_keys]
    current_arr = [current_dist.get(k, 0) for k in all_keys]

    js_div = jensen_shannon_divergence(baseline_arr, current_arr)

    # for display pick the most interesting value
    baseline_val = max(baseline_dist.values()) if baseline_dist else 0
    current_val = max(current_dist.values()) if current_dist else 0
    change = (current_val - baseline_val) / baseline_val * 100 if baseline_val > 0 else 0

    return DriftMetric(
        name=name,
        baseline_value=round(baseline_val, 3),
        current_value=round(current_val, 3),
        change_pct=round(change, 1),
        js_divergence=round(js_div, 4),
        status=determine_status(js_div, thresholds)
    )


def run_drift_analysis(
    baseline_outputs: List[ParserOutput],
    current_outputs: List[ParserOutput],
    baseline_source: str = "day0",
    current_source: str = "day1"
) -> DriftReport:
    """
    compare baseline vs current parser outputs
    """
    run_id = f"drift-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    thresholds = config.drift

    baseline_items = get_all_items(baseline_outputs)
    current_items = get_all_items(current_outputs)

    metrics = []
    alerts = []

    # extraction volume
    base_vol = compute_extraction_volume(baseline_outputs)
    curr_vol = compute_extraction_volume(current_outputs)
    vol_change = (curr_vol["mean"] - base_vol["mean"]) / base_vol["mean"] * 100 if base_vol["mean"] > 0 else 0

    vol_status = DriftStatus.STABLE
    if abs(vol_change) > 50:
        vol_status = DriftStatus.BREAKAGE
    elif abs(vol_change) > thresholds.volume_change_pct:
        vol_status = DriftStatus.DRIFT

    metrics.append(DriftMetric(
        name="extraction_volume",
        baseline_value=round(base_vol["mean"], 2),
        current_value=round(curr_vol["mean"], 2),
        change_pct=round(vol_change, 1),
        status=vol_status
    ))

    if vol_status != DriftStatus.STABLE:
        alerts.append(f"WARNING: extraction volume changed {vol_change:+.1f}%")

    # uncertainty rate
    base_unc = compute_uncertainty_rate(baseline_items)
    curr_unc = compute_uncertainty_rate(current_items)
    unc_change = (curr_unc - base_unc) * 100

    unc_status = DriftStatus.STABLE
    if curr_unc > 0.6:
        unc_status = DriftStatus.BREAKAGE
    elif unc_change > 15:
        unc_status = DriftStatus.DRIFT

    metrics.append(DriftMetric(
        name="uncertainty_rate",
        baseline_value=round(base_unc, 3),
        current_value=round(curr_unc, 3),
        change_pct=round(unc_change, 1),
        status=unc_status
    ))

    # domain mix
    base_domain = compute_domain_distribution(baseline_items)
    curr_domain = compute_domain_distribution(current_items)
    domain_metric = compare_distributions(base_domain, curr_domain, "domain_mix", thresholds)
    metrics.append(domain_metric)

    # check for specific domain surges
    for domain in ["mind", "emotion"]:
        base_pct = base_domain.get(domain, 0)
        curr_pct = curr_domain.get(domain, 0)
        shift = (curr_pct - base_pct) * 100
        if shift > thresholds.domain_shift_pct:
            alerts.append(f"WARNING: {domain} domain surged {shift:+.1f}% (was {base_pct*100:.1f}%, now {curr_pct*100:.1f}%)")

    # arousal distribution
    base_arousal = compute_arousal_distribution(baseline_items)
    curr_arousal = compute_arousal_distribution(current_items)
    arousal_metric = compare_distributions(base_arousal, curr_arousal, "arousal_distribution", thresholds)
    metrics.append(arousal_metric)

    # check for arousal collapse
    if curr_arousal.get("high", 0) > 0.9 and base_arousal.get("high", 0) < 0.7:
        alerts.append(f"CRITICAL: arousal collapsed to {curr_arousal.get('high', 0)*100:.0f}% high")

    # intensity distribution for non-emotion domains
    base_intensity = compute_intensity_distribution(baseline_items)
    curr_intensity = compute_intensity_distribution(current_items)
    intensity_metric = compare_distributions(base_intensity, curr_intensity, "intensity_distribution", thresholds)
    metrics.append(intensity_metric)

    # confidence distribution using ks test
    base_conf = [i.confidence for i in baseline_items]
    curr_conf = [i.confidence for i in current_items]
    ks_stat, ks_pval = ks_test(base_conf, curr_conf)

    conf_status = DriftStatus.STABLE
    if ks_pval < 0.01:
        conf_status = DriftStatus.BREAKAGE
    elif ks_pval < 0.05:
        conf_status = DriftStatus.DRIFT

    base_conf_mean = sum(base_conf) / len(base_conf) if base_conf else 0
    curr_conf_mean = sum(curr_conf) / len(curr_conf) if curr_conf else 0
    conf_change = (curr_conf_mean - base_conf_mean) / base_conf_mean * 100 if base_conf_mean > 0 else 0

    metrics.append(DriftMetric(
        name="confidence_distribution",
        baseline_value=round(base_conf_mean, 3),
        current_value=round(curr_conf_mean, 3),
        change_pct=round(conf_change, 1),
        ks_statistic=ks_stat,
        ks_pvalue=ks_pval,
        status=conf_status
    ))

    if domain_metric.status == DriftStatus.BREAKAGE:
        alerts.append("CRITICAL: significant domain distribution shift detected")

    if arousal_metric.status == DriftStatus.BREAKAGE:
        alerts.append("CRITICAL: significant arousal distribution shift detected")

    if conf_status != DriftStatus.STABLE:
        alerts.append(f"WARNING: confidence distribution shifted (KS p={ks_pval:.4f})")

    # define what normal looks like for each metric
    normal_defs = {
        "extraction_volume": "1-2 items per journal, zero_rate < 10%",
        "uncertainty_rate": "< 40% of items with unknown/low confidence",
        "domain_mix": "symptom 30-40%, food 20-30%, emotion 20-30%, mind 10-20%",
        "arousal_distribution": "low 30-40%, medium 30-40%, high 20-30%",
        "intensity_distribution": "low 20-30%, medium 40-50%, high 20-30%",
        "confidence_distribution": "mean > 0.6, std < 0.2"
    }

    return DriftReport(
        timestamp=datetime.now(),
        run_id=run_id,
        baseline_source=baseline_source,
        current_source=current_source,
        metrics=metrics,
        alerts=alerts,
        thresholds_used={
            "js_drift": thresholds.js_drift,
            "js_breakage": thresholds.js_breakage,
            "domain_shift_pct": thresholds.domain_shift_pct,
            "volume_change_pct": thresholds.volume_change_pct
        },
        normal_definitions=normal_defs
    )
