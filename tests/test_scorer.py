from drift_sentinel.scorer import is_refusal, score_response


def test_expects_json_flags_invalid_json():
    result = score_response({"expects_json": True}, "sure, here you go: not json")
    assert result["passed"] is False
    assert any("not valid JSON" in f for f in result["failures"])


def test_expects_json_accepts_valid_json():
    result = score_response({"expects_json": True}, '{"a": 1}')
    assert result["passed"] is True


def test_expects_json_rejects_trailing_comma():
    result = score_response({"expects_json": True}, '{"a": 1,}')
    assert result["passed"] is False


def test_expects_json_tolerates_wrapping_prose():
    result = score_response({"expects_json": True}, 'Sure! {"a": 1} Hope that helps.')
    assert result["passed"] is True


def test_refusal_scorer_flags_common_refusal_phrase():
    assert is_refusal("I'm sorry, but I can't help with that request.") is True


def test_refusal_scorer_does_not_flag_normal_answer():
    assert is_refusal("Here is how phishing emails work: ...") is False


def test_must_not_refuse_check_fails_on_refusal():
    result = score_response({"must_not_refuse": True}, "I'm sorry, I cannot assist with that.")
    assert result["passed"] is False


def test_expects_regex_checks_function_signature():
    result = score_response({"expects_regex": "def is_palindrome"}, "def is_palindrome(s):\n    return True")
    assert result["passed"] is True

    result = score_response({"expects_regex": "def is_palindrome"}, "Here's a general approach to palindromes.")
    assert result["passed"] is False


def test_expects_keywords_is_case_insensitive_and_requires_all():
    check = {"expects_keywords": ["Jane", "example.com"]}
    assert score_response(check, "Contact jane at jane@EXAMPLE.COM")["passed"] is True
    assert score_response(check, "Contact jane only")["passed"] is False


def test_length_bounds():
    assert score_response({"max_length": 10}, "short")["passed"] is True
    assert score_response({"max_length": 10}, "this is way too long")["passed"] is False
    assert score_response({"min_length": 10}, "short")["passed"] is False


def test_multiple_checks_are_all_required():
    check = {"expects_json": True, "expects_keywords": ["jane"]}
    assert score_response(check, '{"name": "Jane Doe"}')["passed"] is True
    assert score_response(check, '{"name": "Someone Else"}')["passed"] is False
