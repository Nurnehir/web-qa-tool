CATEGORY_WEIGHTS = {
    "security": 0.40,
    "seo": 0.30,
    "link": 0.20,
    "accessibility": 0.10,
}

STATUS_SCORES = {"pass": 100, "warn": 50, "fail": 0}


def calculate_quality_score(findings: list) -> float:
    """
    Bulguları ağırlıklı ortalama ile 0-100 arası skora dönüştürür.
    """
    category_scores: dict = {}
    category_counts: dict = {}

    for f in findings:
        cat = f.category
        score = STATUS_SCORES.get(f.status, 0)
        category_scores[cat] = category_scores.get(cat, 0) + score
        category_counts[cat] = category_counts.get(cat, 0) + 1

    total_score = 0.0
    total_weight = 0.0

    for cat, weight in CATEGORY_WEIGHTS.items():
        if cat in category_scores and category_counts[cat] > 0:
            avg = category_scores[cat] / category_counts[cat]
            total_score += avg * weight
            total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(total_score / total_weight, 1)
