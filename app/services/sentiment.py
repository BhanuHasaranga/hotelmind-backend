_POSITIVE_WORDS = {
    "great", "excellent", "amazing", "wonderful", "good", "clean", "friendly",
    "comfortable", "lovely", "perfect", "fantastic", "helpful", "beautiful",
    "delicious", "recommend", "enjoyed", "best", "awesome", "pleasant",
}
_NEGATIVE_WORDS = {
    "bad", "terrible", "dirty", "rude", "awful", "poor", "worst", "disappointing",
    "noisy", "uncomfortable", "slow", "cold", "broken", "smelly", "unhelpful",
    "horrible", "never", "avoid", "disgusting",
}


def score_sentiment(text: str | None) -> tuple[str, float]:
    """Trivial keyword-based sentiment scoring — no real ML model, kept minimal
    per Phase 7 scope. Returns (label, score) where score is in [-1.0, 1.0].
    """
    if not text:
        return "NEUTRAL", 0.0

    words = [w.strip(".,!?;:\"'").lower() for w in text.split()]
    pos_hits = sum(1 for w in words if w in _POSITIVE_WORDS)
    neg_hits = sum(1 for w in words if w in _NEGATIVE_WORDS)
    total_hits = pos_hits + neg_hits

    if total_hits == 0:
        return "NEUTRAL", 0.0

    score = (pos_hits - neg_hits) / total_hits
    if score > 0.15:
        label = "POSITIVE"
    elif score < -0.15:
        label = "NEGATIVE"
    else:
        label = "NEUTRAL"
    return label, round(score, 3)
