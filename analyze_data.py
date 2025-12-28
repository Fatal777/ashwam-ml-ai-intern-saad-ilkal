"""
Deep analysis script for understanding the exact data patterns and edge cases.
"""
import json
from collections import defaultdict, Counter

def load_jsonl(path):
    with open(path, encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]

def analyze_parser_outputs(path, label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    
    data = load_jsonl(path)
    all_items = [item for record in data for item in record.get('items', [])]
    
    # Basic counts
    print(f"\nTotal journals: {len(data)}")
    print(f"Total items extracted: {len(all_items)}")
    print(f"Empty journals (no items): {sum(1 for d in data if not d.get('items'))}")
    print(f"Avg items per journal: {len(all_items)/len(data):.2f}")
    
    # Domain distribution
    domains = Counter(item.get('domain') for item in all_items)
    print(f"\nDomain distribution:")
    for domain, count in sorted(domains.items()):
        print(f"  {domain}: {count} ({100*count/len(all_items):.1f}%)")
    
    # Field presence analysis
    print(f"\nField presence in items:")
    fields = ['domain', 'text', 'evidence_span', 'polarity', 'time_bucket', 
              'intensity_bucket', 'arousal_bucket', 'confidence']
    for field in fields:
        present = sum(1 for i in all_items if i.get(field) is not None)
        print(f"  {field}: {present}/{len(all_items)}")
    
    # Arousal bucket (for emotions)
    emotion_items = [i for i in all_items if i.get('domain') == 'emotion']
    if emotion_items:
        arousal = Counter(i.get('arousal_bucket') for i in emotion_items)
        print(f"\nArousal distribution (emotion domain only, n={len(emotion_items)}):")
        for bucket, count in sorted(arousal.items(), key=lambda x: str(x[0])):
            print(f"  {bucket}: {count} ({100*count/len(emotion_items):.1f}%)")
    
    # Intensity bucket
    intensity_items = [i for i in all_items if i.get('intensity_bucket') is not None]
    if intensity_items:
        intensity = Counter(i.get('intensity_bucket') for i in intensity_items)
        print(f"\nIntensity distribution (n={len(intensity_items)}):")
        for bucket, count in sorted(intensity.items(), key=lambda x: str(x[0])):
            print(f"  {bucket}: {count}")
    
    # Confidence range
    confidences = [i.get('confidence') for i in all_items if i.get('confidence') is not None]
    if confidences:
        print(f"\nConfidence: min={min(confidences):.2f}, max={max(confidences):.2f}, avg={sum(confidences)/len(confidences):.2f}")
    
    # Polarity distribution
    polarities = Counter(i.get('polarity') for i in all_items)
    print(f"\nPolarity distribution:")
    for pol, count in sorted(polarities.items()):
        print(f"  {pol}: {count}")
    
    # Time bucket distribution
    time_buckets = Counter(i.get('time_bucket') for i in all_items)
    print(f"\nTime bucket distribution:")
    for tb, count in sorted(time_buckets.items(), key=lambda x: str(x[0])):
        print(f"  {tb}: {count}")
    
    return data, all_items

def check_hallucinations(parser_outputs, journals_path):
    """Check if evidence spans exist in source journals"""
    journals = {j['journal_id']: j['text'] for j in load_jsonl(journals_path)}
    
    print(f"\n{'='*60}")
    print("  HALLUCINATION CHECK")
    print(f"{'='*60}")
    
    hallucinations = []
    total_items = 0
    
    for record in parser_outputs:
        journal_id = record['journal_id']
        journal_text = journals.get(journal_id, '')
        
        for item in record.get('items', []):
            total_items += 1
            evidence = item.get('evidence_span', '')
            
            # Case-insensitive substring check
            if evidence.lower() not in journal_text.lower():
                hallucinations.append({
                    'journal_id': journal_id,
                    'evidence_span': evidence,
                    'domain': item.get('domain'),
                    'journal_text': journal_text[:100] + '...' if len(journal_text) > 100 else journal_text
                })
    
    print(f"\nTotal items checked: {total_items}")
    print(f"Hallucinated spans found: {len(hallucinations)}")
    if hallucinations:
        print(f"\nHallucination details:")
        for h in hallucinations:
            print(f"  Journal {h['journal_id']}: '{h['evidence_span']}' (domain: {h['domain']})")
            print(f"    Source text: {h['journal_text']}")
    
    return hallucinations

def check_contradictions(parser_outputs):
    """Check for same evidence span with different polarity"""
    print(f"\n{'='*60}")
    print("  CONTRADICTION CHECK")
    print(f"{'='*60}")
    
    contradictions = []
    
    for record in parser_outputs:
        journal_id = record['journal_id']
        items = record.get('items', [])
        
        # Group by evidence span
        span_map = defaultdict(list)
        for item in items:
            span = item.get('evidence_span', '').lower().strip()
            span_map[span].append(item)
        
        # Find conflicting polarities
        for span, span_items in span_map.items():
            polarities = set(i.get('polarity') for i in span_items)
            if len(polarities) > 1:
                contradictions.append({
                    'journal_id': journal_id,
                    'evidence_span': span,
                    'polarities': list(polarities),
                    'items': span_items
                })
    
    print(f"\nContradictions found: {len(contradictions)}")
    if contradictions:
        for c in contradictions:
            print(f"\n  Journal {c['journal_id']}: '{c['evidence_span']}'")
            print(f"    Conflicting polarities: {c['polarities']}")
            for item in c['items']:
                print(f"      - {item.get('domain')}: polarity={item.get('polarity')}, confidence={item.get('confidence')}")
    
    return contradictions

def analyze_canary():
    """Analyze canary data structure"""
    print(f"\n{'='*60}")
    print("  CANARY DATA ANALYSIS")
    print(f"{'='*60}")
    
    canary_journals = load_jsonl('data/canary/journals.jsonl')
    gold = load_jsonl('data/canary/gold.jsonl')
    
    print(f"\nCanary journals: {len(canary_journals)}")
    print(f"Gold labels: {len(gold)}")
    
    # Compare schema between gold and parser outputs
    print(f"\nGold label schema (first item):")
    if gold and gold[0].get('items'):
        first_item = gold[0]['items'][0]
        for key, value in first_item.items():
            print(f"  {key}: {type(value).__name__} = {value}")
    
    # Check what fields gold has vs parser output has
    gold_items = [item for record in gold for item in record.get('items', [])]
    print(f"\nTotal gold items: {len(gold_items)}")
    
    gold_fields = set()
    for item in gold_items:
        gold_fields.update(item.keys())
    print(f"Fields in gold: {sorted(gold_fields)}")
    
    # Domain distribution in gold
    gold_domains = Counter(item.get('domain') for item in gold_items)
    print(f"\nGold domain distribution:")
    for domain, count in sorted(gold_domains.items()):
        print(f"  {domain}: {count}")

def compare_day0_day1():
    """Direct comparison between Day0 and Day1"""
    print(f"\n{'='*60}")
    print("  DAY0 vs DAY1 COMPARISON")
    print(f"{'='*60}")
    
    d0 = load_jsonl('data/parser_outputs_day0.jsonl')
    d1 = load_jsonl('data/parser_outputs_day1.jsonl')
    
    items0 = [item for record in d0 for item in record.get('items', [])]
    items1 = [item for record in d1 for item in record.get('items', [])]
    
    # Domain shift
    domains0 = Counter(item.get('domain') for item in items0)
    domains1 = Counter(item.get('domain') for item in items1)
    
    print(f"\nDomain shift:")
    print(f"  {'Domain':<12} {'Day0':>8} {'Day1':>8} {'Change':>10}")
    print(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*10}")
    all_domains = set(domains0.keys()) | set(domains1.keys())
    for domain in sorted(all_domains):
        d0_count = domains0.get(domain, 0)
        d1_count = domains1.get(domain, 0)
        d0_pct = 100 * d0_count / len(items0) if items0 else 0
        d1_pct = 100 * d1_count / len(items1) if items1 else 0
        print(f"  {domain:<12} {d0_pct:>7.1f}% {d1_pct:>7.1f}% {d1_pct-d0_pct:>+9.1f}%")
    
    # Arousal shift for emotions
    emo0 = [i for i in items0 if i.get('domain') == 'emotion']
    emo1 = [i for i in items1 if i.get('domain') == 'emotion']
    
    arousal0 = Counter(i.get('arousal_bucket') for i in emo0)
    arousal1 = Counter(i.get('arousal_bucket') for i in emo1)
    
    print(f"\nArousal shift (emotion domain):")
    print(f"  {'Bucket':<12} {'Day0':>8} {'Day1':>8}")
    for bucket in ['low', 'medium', 'high']:
        d0_pct = 100 * arousal0.get(bucket, 0) / len(emo0) if emo0 else 0
        d1_pct = 100 * arousal1.get(bucket, 0) / len(emo1) if emo1 else 0
        print(f"  {bucket:<12} {d0_pct:>7.1f}% {d1_pct:>7.1f}%")
    
    # Confidence shift
    conf0 = [i.get('confidence') for i in items0 if i.get('confidence')]
    conf1 = [i.get('confidence') for i in items1 if i.get('confidence')]
    
    print(f"\nConfidence shift:")
    print(f"  Day0 avg: {sum(conf0)/len(conf0):.3f}")
    print(f"  Day1 avg: {sum(conf1)/len(conf1):.3f}")

if __name__ == '__main__':
    # Analyze Day0
    d0_data, d0_items = analyze_parser_outputs('data/parser_outputs_day0.jsonl', 'DAY 0 - BASELINE')
    
    # Analyze Day1
    d1_data, d1_items = analyze_parser_outputs('data/parser_outputs_day1.jsonl', 'DAY 1 - DRIFT/BREAKAGE')
    
    # Check hallucinations in both
    print("\n" + "="*60)
    print("  DAY 0 HALLUCINATION CHECK")
    check_hallucinations(d0_data, 'data/journals.jsonl')
    
    print("\n" + "="*60)
    print("  DAY 1 HALLUCINATION CHECK")
    h1 = check_hallucinations(d1_data, 'data/journals.jsonl')
    
    # Check contradictions
    print("\n" + "="*60)
    print("  DAY 0 CONTRADICTIONS")
    check_contradictions(d0_data)
    
    print("\n" + "="*60)
    print("  DAY 1 CONTRADICTIONS")
    c1 = check_contradictions(d1_data)
    
    # Canary analysis
    analyze_canary()
    
    # Comparison
    compare_day0_day1()
    
    print("\n" + "="*60)
    print("  SUMMARY OF ISSUES IN DAY1")
    print("="*60)
    print(f"\n  Hallucinations: {len(h1)}")
    print(f"  Contradictions: {len(c1)}")
