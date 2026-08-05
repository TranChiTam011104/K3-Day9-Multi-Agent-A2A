"""
Coordinator Agent
Điều phối toàn bộ multi-agent pipeline.
Nhận case input, gọi từng agent theo thứ tự, tổng hợp và ghi output.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from src.data_loader import get_order_with_details
from src.agents import order_seller_agent, payment_agent, delivery_agent, policy_agent, verifier_agent
from src.trace_logger import get_trace_logger

logger = logging.getLogger(__name__)

INPUT_DIR = Path(__file__).parent.parent.parent / "input"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def process_case(case_id: str) -> bool:
    """
    Xử lý một case bằng cách chạy toàn bộ multi-agent pipeline.

    Pipeline:
        Coordinator → Order/Seller → Payment → Delivery → Policy → Verifier → Write Output

    Args:
        case_id: Case ID (e.g., "EC_001")

    Returns:
        True nếu thành công, False nếu có lỗi
    """
    tracer = get_trace_logger()

    try:
        # Read input
        input_file = INPUT_DIR / f"{case_id}.json"
        if not input_file.exists():
            raise FileNotFoundError(f"Input not found: {input_file}")

        with open(input_file, "r", encoding="utf-8") as f:
            case_input = json.load(f)

        order_id = case_input.get("customer_request", {}).get("claimed_order_id", "")
        if not order_id:
            raise ValueError(f"Missing claimed_order_id in {case_id}")

        tracer.log_start(case_id, order_id)
        tracer.log_agent(case_id, "Coordinator", "received_case", {"order_id": order_id})
        logger.info(f"\n{'='*60}\n[{case_id}] Starting pipeline for order: {order_id}")

        # Load raw data from CSV (Coordinator does the DB query)
        order_data = get_order_with_details(order_id)
        if "error" in order_data:
            raise ValueError(f"Order not found: {order_id}")

        tracer.log_agent(case_id, "Coordinator", "fetched_order_data", {
            "status": order_data.get("order", {}).get("order_status"),
            "items_count": order_data.get("items_count"),
            "payments_count": order_data.get("payments_count"),
        })

        # Build initial context - shared state passed between agents
        context: Dict[str, Any] = {
            "case_id": case_id,
            "order_id": order_id,
            "order_data": order_data,
        }

        # === Agent 1: Order & Seller Agent ===
        logger.info(f"[{case_id}] → Order & Seller Agent")
        context = order_seller_agent.run(context)
        tracer.log_agent(case_id, "OrderSellerAgent", "analyzed",
                         context.get("order_seller_analysis", {}))

        # === Agent 2: Payment Agent ===
        logger.info(f"[{case_id}] → Payment Agent")
        context = payment_agent.run(context)
        tracer.log_agent(case_id, "PaymentAgent", "analyzed",
                         context.get("payment_analysis", {}))

        # === Agent 3: Delivery Agent ===
        logger.info(f"[{case_id}] → Delivery Agent")
        context = delivery_agent.run(context)
        tracer.log_agent(case_id, "DeliveryAgent", "analyzed",
                         context.get("delivery_analysis", {}))

        # === Agent 4: Policy Agent ===
        logger.info(f"[{case_id}] → Policy Agent")
        context = policy_agent.run(context)
        policy_res = context.get("policy_result", {})
        tracer.log_agent(case_id, "PolicyAgent", "applied_policy", policy_res)
        tracer.log_policy(case_id, policy_res.get("primary_issue", "unknown"),
                          policy_res.get("confidence", 0.0))

        # === Agent 5: Verifier Agent ===
        logger.info(f"[{case_id}] → Verifier Agent")
        context = verifier_agent.run(context)
        tracer.log_agent(case_id, "VerifierAgent", "verified", {"status": "ok"})

        # === Write output ===
        final_output = context["final_output"]
        OUTPUT_DIR.mkdir(exist_ok=True)
        output_path = OUTPUT_DIR / f"{case_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)

        tracer.log_agent(case_id, "Coordinator", "wrote_output", {"path": str(output_path)})
        tracer.log_end(case_id, "success")
        logger.info(f"[{case_id}] ✓ Done: {policy_res.get('primary_issue')} | refund={policy_res.get('recommended_refund_brl')}")
        return True

    except Exception as e:
        logger.error(f"[{case_id}] ✗ Failed: {e}")
        tracer.log_error(case_id, e)
        tracer.log_end(case_id, "failed")
        return False
