"""
Main entry point for Multi-Agent E-commerce Dispute Resolution System.
Model: Gemini 2.0 Flash (< 8B parameter class, via Google AI Studio API)
"""

import sys
import logging
import argparse
from pathlib import Path

# Load .env first
from dotenv import load_dotenv
load_dotenv()

from src.data_loader import preload_all_data, list_input_cases
from src.agents.coordinator import process_case
from src.trace_logger import write_trace, get_trace_logger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent E-commerce Dispute Resolution System (Gemini 2.0 Flash)"
    )
    parser.add_argument("--case", type=str, help="Process specific case (e.g., EC_001)")
    parser.add_argument("--list-cases", action="store_true", help="List all input cases")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Preload data into cache to avoid repeated CSV reads
    logger.info("Preloading CSV data into cache...")
    preload_all_data()
    logger.info("Data preloaded successfully.")

    if args.list_cases:
        cases = list_input_cases()
        print(f"\nFound {len(cases)} input cases:")
        for c in cases:
            print(f"  - {c}")
        return

    if args.case:
        success = process_case(args.case)
        write_trace()
        sys.exit(0 if success else 1)

    # Process all 50 cases
    cases = list_input_cases()
    logger.info(f"\nProcessing {len(cases)} cases with Multi-Agent Pipeline...")
    logger.info(f"Model: gpt-4o-mini (OpenAI Small class, < 8B parameters)")
    logger.info("="*60)

    results = {}
    for i, case_id in enumerate(cases):
        results[case_id] = process_case(case_id)
        # Small delay between cases to avoid rate limiting
        # Each case makes ~4 LLM calls, so space them out
        if i < len(cases) - 1:
            import time
            time.sleep(0.5)  # Small gap between cases

    # Write full trace
    write_trace()

    # Summary
    success_count = sum(1 for v in results.values() if v)
    failed_count = len(results) - success_count

    logger.info("\n" + "="*60)
    logger.info("PROCESSING COMPLETE")
    logger.info(f"  ✓ Success: {success_count}/{len(cases)}")
    logger.info(f"  ✗ Failed:  {failed_count}/{len(cases)}")

    if failed_count > 0:
        logger.info("\nFailed cases:")
        for cid, ok in results.items():
            if not ok:
                logger.info(f"  - {cid}")

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
