"""
Output Writer Module
Ghi kß║┐t quß║ú xuß╗æng JSON files.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def ensure_output_dir():
    """─Éß║úm bß║úo th╞░ mß╗Ñc output tß╗ôn tß║íi."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_output(
    case_id: str,
    primary_issue: str,
    case_status: str,
    confidence: float,
    order_ids: List[str],
    item_ids: List[str],
    seller_ids: List[str],
    payment_ids: List[str],
    ranked_causes: List[Dict[str, Any]],
    responsible_parties: List[Dict[str, str]],
    evidence_ids: List[str],
    item_total_brl: float,
    freight_total_brl: float,
    payment_total_brl: float,
    recommended_refund_brl: float,
    resolution_actions: List[str],
) -> Dict[str, Any]:
    """
    Build output dict theo schema.

    Args:
        case_id: Case ID (e.g., "EC_001")
        primary_issue: Primary issue code
        case_status: "action_required" or "no_action"
        confidence: Confidence score [0, 1]
        order_ids: List of order IDs
        item_ids: List of item IDs (format: order_id:item_id)
        seller_ids: List of seller IDs
        payment_ids: List of payment IDs (format: order_id:sequential)
        ranked_causes: List of cause dicts with cause_code and rank
        responsible_parties: List of party dicts with party_type and party_id
        evidence_ids: List of evidence IDs
        item_total_brl: Total item amount
        freight_total_brl: Total freight amount
        payment_total_brl: Total payment amount
        recommended_refund_brl: Recommended refund amount
        resolution_actions: List of resolution actions

    Returns:
        Output dict theo schema
    """
    return {
        "case_id": case_id,
        "assessment": {
            "primary_issue": primary_issue,
            "case_status": case_status,
            "confidence": round(confidence, 2),
        },
        "affected_entities": {
            "order_ids": order_ids[:5],  # Max 5
            "item_ids": item_ids[:5],  # Max 5
            "seller_ids": seller_ids[:5],  # Max 5
            "payment_ids": payment_ids[:5],  # Max 5
        },
        "root_cause_analysis": {
            "ranked_causes": ranked_causes[:3],  # Max 3
            "responsible_parties": responsible_parties[:3],  # Max 3
        },
        "evidence_ids": evidence_ids[:10],  # Max 10
        "financial_resolution": {
            "currency": "BRL",
            "item_total_brl": round(item_total_brl, 2),
            "freight_total_brl": round(freight_total_brl, 2),
            "payment_total_brl": round(payment_total_brl, 2),
            "recommended_refund_brl": round(recommended_refund_brl, 2),
        },
        "resolution_actions": resolution_actions[:5],  # Max 5
    }


def write_output(case_id: str, output: Dict[str, Any]) -> Path:
    """
    Ghi output xuß╗æng file JSON.

    Args:
        case_id: Case ID (e.g., "EC_001")
        output: Output dict

    Returns:
        Path ─æß║┐n file ─æ├ú ghi
    """
    ensure_output_dir()
    filename = f"{case_id}.json"
    filepath = OUTPUT_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(f"Wrote output: {filepath}")
    return filepath


def read_input(case_id: str) -> Dict[str, Any]:
    """
    ─Éß╗ìc input file.

    Args:
        case_id: Case ID (e.g., "EC_001")

    Returns:
        Input dict
    """
    input_dir = Path(__file__).parent.parent / "input"
    filepath = input_dir / f"{case_id}.json"

    if not filepath.exists():
        raise FileNotFoundError(f"Input file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_case_order_id(case: Dict[str, Any]) -> str:
    """
    Tr├¡ch xuß║Ñt order_id tß╗½ case input.

    Args:
        case: Input case dict

    Returns:
        Order ID
    """
    return case.get("customer_request", {}).get("claimed_order_id", "")


def list_input_cases() -> List[str]:
    """
    Liß╗çt k├¬ tß║Ñt cß║ú input cases.

    Returns:
        List cß╗ºa case IDs (e.g., ["EC_001", "EC_002", ...])
    """
    input_dir = Path(__file__).parent.parent / "input"
    case_ids = []

    for f in input_dir.glob("EC_*.json"):
        case_id = f.stem
        case_ids.append(case_id)

    return sorted(case_ids)


def count_output_files() -> int:
    """
    ─Éß║┐m sß╗æ file trong output directory.

    Returns:
        Sß╗æ l╞░ß╗úng file
    """
    if not OUTPUT_DIR.exists():
        return 0
    return len(list(OUTPUT_DIR.glob("EC_*.json")))


def verify_all_outputs(expected_count: int = 50) -> Dict[str, Any]:
    """
    Verify tß║Ñt cß║ú outputs ─æ├ú ─æ╞░ß╗úc tß║ío.

    Args:
        expected_count: Sß╗æ l╞░ß╗úng expected outputs

    Returns:
        Dict vß╗¢i th├┤ng tin verification
    """
    case_ids = list_input_cases()
    output_count = count_output_files()

    missing = []
    for case_id in case_ids:
        output_file = OUTPUT_DIR / f"{case_id}.json"
        if not output_file.exists():
            missing.append(case_id)

    return {
        "expected": expected_count,
        "found": output_count,
        "missing_count": len(missing),
        "missing_cases": missing,
        "all_present": len(missing) == 0,
    }
