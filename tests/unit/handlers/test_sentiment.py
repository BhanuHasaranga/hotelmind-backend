from app.services.sentiment import score_sentiment


def test_positive_sentiment():
    label, score = score_sentiment("The room was great and the staff were friendly and helpful")
    assert label == "POSITIVE"
    assert score > 0


def test_negative_sentiment():
    label, score = score_sentiment("The room was dirty and the staff were rude")
    assert label == "NEGATIVE"
    assert score < 0


def test_neutral_sentiment_no_keywords():
    label, score = score_sentiment("The room had a view of the parking lot")
    assert label == "NEUTRAL"
    assert score == 0.0


def test_empty_comment_is_neutral():
    label, score = score_sentiment(None)
    assert label == "NEUTRAL"
    assert score == 0.0
