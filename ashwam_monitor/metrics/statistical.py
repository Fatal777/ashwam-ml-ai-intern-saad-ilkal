import numpy as np
from scipy import stats
from scipy.stats import entropy
from typing import List, Tuple, Dict


def jensen_shannon_divergence(p: List[float], q: List[float]) -> float:
    # symmetric measure of distribution divergence, returns 0 to 1 where 0 is identical
    p = np.asarray(p, dtype=float)
    q = np.asarray(q, dtype=float)

    p = np.clip(p, 1e-10, None)
    q = np.clip(q, 1e-10, None)

    p = p / p.sum()
    q = q / q.sum()

    m = 0.5 * (p + q)
    return float(0.5 * (entropy(p, m) + entropy(q, m)))


import warnings

def ks_test(baseline: List[float], current: List[float]) -> Tuple[float, float]:
    # kolmogorov smirnov test, returns (statistic, pvalue), pvalue < 0.05 means significantly different
    if len(baseline) < 2 or len(current) < 2:
        return 0.0, 1.0

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stat, pval = stats.ks_2samp(baseline, current)
    return float(stat), float(pval)


def chi_squared_test(baseline_counts: Dict[str, int], current_counts: Dict[str, int]) -> Tuple[float, float]:
    # chi squared for categorical distributions, returns (statistic, pvalue)
    categories = sorted(set(baseline_counts.keys()) | set(current_counts.keys()))

    observed = [current_counts.get(c, 0) for c in categories]
    expected = [baseline_counts.get(c, 0) for c in categories]

    total_obs = sum(observed)
    total_exp = sum(expected)

    if total_exp == 0:
        return 0.0, 1.0

    expected = [e * total_obs / total_exp for e in expected]

    valid = [(o, e) for o, e in zip(observed, expected) if e > 0]
    if len(valid) < 2:
        return 0.0, 1.0

    obs = [v[0] for v in valid]
    exp = [v[1] for v in valid]

    stat, pval = stats.chisquare(obs, exp)
    return float(stat), float(pval)


def compute_distribution(items: List, key_fn) -> Dict[str, float]:
    # compute percentage distribution for a list of items, key_fn extracts category
    if not items:
        return {}

    counts = {}
    for item in items:
        k = key_fn(item)
        if k is not None:
            counts[k] = counts.get(k, 0) + 1

    total = sum(counts.values())
    if total == 0:
        return {}

    return {k: v / total for k, v in counts.items()}
