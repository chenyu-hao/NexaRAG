def test_answer_verifier_fails_when_answer_contains_unsupported_numbers():
    from agent.verifier import AnswerVerifier

    result = AnswerVerifier._apply_numeric_grounding(
        {"pass": True, "score": 4, "reason": "ok"},
        answer="Charges to 100% in 22 minutes with 125W.",
        context="AUTO Phone Beta supports 125W wired charging.",
    )

    assert result["pass"] is False
    assert result["score"] <= 2
    assert "22" in result["unsupported_numbers"]


def test_answer_verifier_allows_numbers_present_in_context():
    from agent.verifier import AnswerVerifier

    result = AnswerVerifier._apply_numeric_grounding(
        {"pass": True, "score": 4, "reason": "ok"},
        answer="Battery is 5180mAh and wireless charging is 55W.",
        context="Battery 5180mAh. Wireless charging 55W.",
    )

    assert result["pass"] is True
