from cli.score_job_for_user import parse_eval


def test_parse_eval_from_dict():
    score, expl = parse_eval({"score": 88, "explanation": "Strong match on skills"})
    assert score == 88
    assert "Strong" in expl


def test_parse_eval_from_text():
    text = "Score: 72\nExplanation: experience aligns well with the requirements."
    score, expl = parse_eval(text)
    assert score == 72
    assert "aligns well" in expl


def test_parse_eval_missing_score_uses_text_as_explanation():
    text = "No numeric score provided here."
    score, expl = parse_eval(text)
    assert score is None
    assert expl == text


def test_parse_eval_dict_with_nested_explanation():
    score, expl = parse_eval({"score": 67, "evaluation": {"text": "Solid but missing X"}})
    assert score == 67
    assert "missing X" in expl
