"""
Trace Logger Module
Ghi trace cß╗ºa qu├í tr├¼nh xß╗¡ l├╜ 50 cases.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import traceback

logger = logging.getLogger(__name__)

TRACE_FILE = Path(__file__).parent.parent / "trace.jsonl"


class TraceLogger:
    """Logger cho viß╗çc trace execution."""

    def __init__(self):
        self.traces: List[Dict[str, Any]] = []

    def log_start(self, case_id: str, claimed_order_id: str):
        """Log bß║»t ─æß║ºu xß╗¡ l├╜ mß╗Öt case."""
        self.traces.append({
            "event": "start",
            "case_id": case_id,
            "claimed_order_id": claimed_order_id,
            "timestamp": datetime.now().isoformat(),
        })

    def log_agent(self, case_id: str, agent_name: str, action: str, data: Optional[Dict] = None):
        """Log h├ánh ─æß╗Öng cß╗ºa mß╗Öt agent."""
        self.traces.append({
            "event": "agent",
            "case_id": case_id,
            "agent": agent_name,
            "action": action,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })

    def log_policy(self, case_id: str, primary_issue: str, confidence: float):
        """Log kß║┐t quß║ú policy."""
        self.traces.append({
            "event": "policy",
            "case_id": case_id,
            "primary_issue": primary_issue,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
        })

    def log_error(self, case_id: str, error: Exception):
        """Log lß╗ùi."""
        self.traces.append({
            "event": "error",
            "case_id": case_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat(),
        })

    def log_end(self, case_id: str, status: str):
        """Log kß║┐t th├║c xß╗¡ l├╜ case."""
        self.traces.append({
            "event": "end",
            "case_id": case_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        })

    def write(self):
        """Ghi trace ra file JSONL (overwrite)."""
        with open(TRACE_FILE, "w", encoding="utf-8") as f:
            for trace in self.traces:
                f.write(json.dumps(trace, ensure_ascii=False) + "\n")
        logger.info(f"Wrote {len(self.traces)} trace entries to {TRACE_FILE}")

    def read(self) -> List[Dict[str, Any]]:
        """─Éß╗ìc trace tß╗½ file."""
        if not TRACE_FILE.exists():
            return []

        traces = []
        with open(TRACE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                traces.append(json.loads(line))
        return traces

    def get_case_traces(self, case_id: str) -> List[Dict[str, Any]]:
        """Lß║Ñy tß║Ñt cß║ú traces cho mß╗Öt case."""
        return [t for t in self.traces if t.get("case_id") == case_id]

    def get_errors(self) -> List[Dict[str, Any]]:
        """Lß║Ñy tß║Ñt cß║ú lß╗ùi."""
        return [t for t in self.traces if t.get("event") == "error"]

    def clear(self):
        """X├│a tß║Ñt cß║ú traces."""
        self.traces = []


# Global trace logger instance
_global_trace_logger: Optional[TraceLogger] = None


def get_trace_logger() -> TraceLogger:
    """Get hoß║╖c create global trace logger."""
    global _global_trace_logger
    if _global_trace_logger is None:
        _global_trace_logger = TraceLogger()
    return _global_trace_logger


def log_case_start(case_id: str, claimed_order_id: str):
    """Convenience function ─æß╗â log case start."""
    get_trace_logger().log_start(case_id, claimed_order_id)


def log_agent_action(case_id: str, agent_name: str, action: str, data: Optional[Dict] = None):
    """Convenience function ─æß╗â log agent action."""
    get_trace_logger().log_agent(case_id, agent_name, action, data)


def log_policy_result(case_id: str, primary_issue: str, confidence: float):
    """Convenience function ─æß╗â log policy result."""
    get_trace_logger().log_policy(case_id, primary_issue, confidence)


def log_case_error(case_id: str, error: Exception):
    """Convenience function ─æß╗â log case error."""
    get_trace_logger().log_error(case_id, error)


def log_case_end(case_id: str, status: str):
    """Convenience function ─æß╗â log case end."""
    get_trace_logger().log_end(case_id, status)


def write_trace():
    """Convenience function ─æß╗â write trace file."""
    get_trace_logger().write()


def read_trace() -> List[Dict[str, Any]]:
    """Convenience function ─æß╗â read trace file."""
    return get_trace_logger().read()
