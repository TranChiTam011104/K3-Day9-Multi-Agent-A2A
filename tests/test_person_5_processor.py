import json

import pytest

from src.person_5_processor import (
    PERSON_5_CASE_IDS,
    analyze_person_5_case,
    write_person_5_results,
)
from src.validators import validate_evidence_ids


def test_person_5_scope_is_exact() -> None:
    assert PERSON_5_CASE_IDS == tuple(f"EC_{number:03d}" for number in range(41, 51))


def test_rejects_case_outside_person_5_scope() -> None:
    with pytest.raises(ValueError, match="outside Person 5 scope"):
        analyze_person_5_case("EC_040")


def test_canceled_case_preserves_missing_delivery_as_null() -> None:
    result = analyze_person_5_case("EC_041")

    assert result["order_status"] == "canceled"
    assert result["delivery_analysis"]["delivered_customer_date"] is None
    assert result["delivery_analysis"]["delivered_after_estimate"] is None
    assert result["financial_analysis"]["payment_total_brl"] == 53.19
    assert result["financial_analysis"]["is_reconciled"] is True


def test_split_payment_rows_and_evidence_are_preserved() -> None:
    result = analyze_person_5_case("EC_046")
    payment = result["payment_analysis"]

    assert payment["payments_count"] == 2
    assert payment["is_split_payment"] is True
    assert [row["payment_sequential"] for row in payment["payments"]] == [1, 2]
    assert [row["payment_value_brl"] for row in payment["payments"]] == [39.17, 86.84]
    assert f"payment:{result['claimed_order_id']}:1" in result["evidence_ids"]
    assert f"payment:{result['claimed_order_id']}:2" in result["evidence_ids"]


@pytest.mark.parametrize(
    ("case_id", "delivered_after_estimate", "handoff_after_limit"),
    [
        ("EC_043", True, True),
        ("EC_044", True, True),
        ("EC_049", True, False),
        ("EC_050", True, False),
        ("EC_042", False, False),
    ],
)
def test_delivery_and_handoff_facts(
    case_id: str, delivered_after_estimate: bool, handoff_after_limit: bool
) -> None:
    result = analyze_person_5_case(case_id)

    assert result["delivery_analysis"]["delivered_after_estimate"] is delivered_after_estimate
    assert result["delivery_analysis"]["seller_handoffs"][0][
        "handoff_after_shipping_limit"
    ] is handoff_after_limit


@pytest.mark.parametrize("case_id", PERSON_5_CASE_IDS)
def test_financials_and_evidence_are_verified(case_id: str) -> None:
    result = analyze_person_5_case(case_id)
    financials = result["financial_analysis"]

    assert financials["expected_total_brl"] == round(
        financials["item_total_brl"] + financials["freight_total_brl"], 2
    )
    assert financials["difference_brl"] == round(
        financials["payment_total_brl"] - financials["expected_total_brl"], 2
    )
    assert financials["is_reconciled"] is True
    assert validate_evidence_ids(result["evidence_ids"])[0] is True


def test_writes_exactly_the_requested_json_files(tmp_path) -> None:
    selected = ("EC_041", "EC_046")
    written = write_person_5_results(case_ids=selected, output_dir=tmp_path)

    assert [path.name for path in written] == ["EC_041.json", "EC_046.json"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["EC_041.json", "EC_046.json"]
    for path in written:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["case_id"] == path.stem
