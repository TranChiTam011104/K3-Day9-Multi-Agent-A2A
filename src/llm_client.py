"""
LLM Client Module
Sử dụng OpenAI gpt-4.1-nano — model nhỏ, nhanh, chất lượng cao.
Hỗ trợ JSON mode (response_format) và retry logic.
"""

import os
import json
import time
import logging
from typing import Any, Dict
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Model name - declared in source code as required by lab rules (NOT in .env)
# gpt-4o-mini: OpenAI's small/efficient model, < 8B parameter class
# Best accuracy for structured JSON output and business rule application
MODEL_NAME = "gpt-4o-mini"


def _get_client():
    """Khởi tạo OpenAI client."""
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Please add it to your .env file."
            )
        return OpenAI(api_key=api_key)
    except ImportError:
        raise ImportError("openai not installed. Run: pip install openai")


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 3,
    temperature: float = 0.0,
) -> Dict[str, Any]:
    """
    Gọi OpenAI và trả về JSON output.

    Args:
        system_prompt: System instructions
        user_prompt: User message với dữ liệu cần phân tích
        max_retries: Số lần retry khi gặp lỗi
        temperature: Độ ngẫu nhiên (0 = deterministic)

    Returns:
        Dict parsed từ JSON response của model
    """
    client = _get_client()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
            )

            text = response.choices[0].message.content.strip()

            # Clean up markdown fences if present
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

            result = json.loads(text)
            logger.debug(f"LLM call successful on attempt {attempt + 1}")
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1.0)
            else:
                raise
        except Exception as e:
            err_str = str(e)
            logger.warning(f"LLM call failed on attempt {attempt + 1}: {err_str[:200]}")
            if "rate_limit" in err_str.lower() or "429" in err_str:
                wait_time = 5.0 * (attempt + 1)
                logger.info(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            elif attempt < max_retries - 1:
                time.sleep(2.0 * (attempt + 1))
            else:
                raise

    raise RuntimeError(f"LLM call failed after {max_retries} retries")
