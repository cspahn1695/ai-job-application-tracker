def test_user_name(stage_user):
    result = stage_user["name"]
    assert result == "Alice"
