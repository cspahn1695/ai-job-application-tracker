import pytest

@pytest.fixture
def first_layer():
    return "a"

@pytest.fixture
def wrap_layer(first_layer):
    return [first_layer]

def test_wrapped_correctly(wrap_layer):
    assert wrap_layer == ["a"]
    wrap_layer.append("b")
    assert wrap_layer == ["a", "b"]