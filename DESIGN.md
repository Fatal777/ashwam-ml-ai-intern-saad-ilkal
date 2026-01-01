# Design Decisions

This document explains the key trade-offs, design choices, and what was intentionally NOT built.

---

## Statistical Method Choices

### Why Jensen-Shannon Divergence (JSD) over PSI?

**Considered:** Population Stability Index (PSI) - common in credit scoring/finance
**Chose:** Jensen-Shannon Divergence

**Reasoning:**
- PSI is asymmetric (baseline vs current matters) - confusing when debugging
- JSD is symmetric, bounded [0, 1], and has information-theoretic interpretation
- In healthcare context, "how different are these distributions?" is more intuitive than "how unstable is the population?"
- JSD handles zero counts gracefully with epsilon smoothing

**When I'd switch:** If stakeholders are familiar with PSI from other domains, consistency might matter more than theoretical elegance.

---

### Why KS Test for Confidence Distributions?

**Considered:** t-test, Mann-Whitney U, chi-squared
**Chose:** Kolmogorov-Smirnov two-sample test

**Reasoning:**
- KS detects *any* distributional difference, not just mean shift
- Confidence scores are continuous [0, 1], not categorical
- t-test assumes normality - confidence scores often aren't
- KS is non-parametric and works on small samples

**Trade-off:** KS is less powerful than t-test when normality holds. Accepted this for robustness.

---

## Threshold Rationale

### Why 5% Hallucination Threshold?

This is actually **too high** for production health apps. Chose 5% because:
- Dataset is synthetic with intentional issues
- Real production would want ≤1%
- 5% allows demonstration of alert triggering

**Production recommendation:** Start at 2%, tune based on false positive rate.

### Why 1% Contradiction Threshold?

Contradictions are **especially harmful**:
- Telling a user "cramps present" AND "cramps absent" destroys trust
- Even 1 contradiction in 100 items is jarring
- Zero-tolerance would be ideal but too brittle for demos

---

## What I Chose NOT to Build

### 1. Semantic Similarity Matching

**Why not:** 
- Simple substring matching works for evidence grounding
- Semantic matching (embeddings) would require model inference
- Adds latency, complexity, failure modes
- False positives from fuzzy matching could flag valid items

**When I would add it:** If parser starts paraphrasing evidence instead of quoting verbatim.

### 2. Real-Time Streaming

**Why not:**
- PRD specifies batch processing (Day 0 vs Day 1)
- Streaming adds architectural complexity (Kafka, Redis, etc.)
- Batch is easier to debug and reason about

**When I would add it:** If monitoring needs to run per-request instead of per-batch.

### 3. Multi-Language NLP

**Why not:**
- Hinglish is code-mixed English + Hindi in Roman script
- Simple string matching works because evidence spans are verbatim
- Adding NLP (tokenization, lemmatization) would slow things down
- Unicode normalization is sufficient

**When I would add it:** If evidence spans need transliteration or if parser starts outputting in Devanagari.

### 4. Interactive Review UI

**Why not:**
- PRD asks for CLI, not web app
- Building UI is scope creep
- `review-queue` CLI command provides the functionality

**When I would add it:** If clinicians need to batch-approve/reject items with notes.

## If I Had More Time

**Production Scale:**
1. **Structured logging** - Log to ELK/Datadog instead of stdout
2. **Database persistence** - Store historical runs for trend analysis
3. **Metrics export** - Prometheus/Grafana integration
4. **Webhook alerts** - POST to Slack/PagerDuty on CRITICAL

**Monitoring Enhancements:**
5. **A/B canary testing** - Compare two model versions side-by-side
6. **Time-series trending** - Detect gradual drift across multiple runs
7. **Semantic similarity** - Use embeddings to catch paraphrased evidence

**Scale Optimizations:**
8. **Sampling for large batches** - Process subset at 10K+ journals
9. **Async processing** - Parallelize invariant checks
10. **Configurable thresholds** - YAML config instead of code

