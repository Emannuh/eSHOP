"""Tests for phone number normalisation."""
import pytest

from apps.orders.services import normalize_phone


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("0712345678", "254712345678"),
        ("07 1234 5678", "254712345678"),
        ("07-1234-5678", "254712345678"),
        ("+254712345678", "254712345678"),
        ("254712345678", "254712345678"),
        ("0112345678", "254112345678"),
        ("+254112345678", "254112345678"),
    ],
)
def test_normalize_phone_valid(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "123",
        "0612345678",   # 06XX not valid in Kenya
        "0812345678",   # 08XX not valid
        "+1 800 555 0100",
        "abcdefghij",
        "",
    ],
)
def test_normalize_phone_invalid(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_phone(raw)
