# tests/unit/test_preprocessing.py
from backend.utils.preprocessing import clean_text, format_input_for_model


def test_clean_text_basic():
    assert clean_text("a   b   c") == "a b c"


def test_clean_text_strip():
    assert clean_text("   hello   ") == "hello"


def test_clean_text_empty():
    assert clean_text("") == ""


def test_format_input_contains_sep():
    out = format_input_for_model("a", "b", "c")
    assert "</s>" in out


def test_format_input_order():
    out = format_input_for_model("ctx", "pr", "res")
    assert out.startswith("ctx")
    assert out.endswith("res")