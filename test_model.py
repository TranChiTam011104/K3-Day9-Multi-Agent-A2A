"""Test OpenAI models that are small (< 8B / mini class)."""
from dotenv import load_dotenv
load_dotenv()
import os, time, json
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: No OPENAI_API_KEY found!")
    exit(1)

print(f"OpenAI Key: {api_key[:12]}...")
client = OpenAI(api_key=api_key)

# Small/mini class models from OpenAI (< 8B equivalent)
candidates = [
    "gpt-4.1-nano",   # Smallest, fastest
    "gpt-4o-mini",    # Popular small model
    "gpt-4.1-mini",   # Mid-tier mini
]

print("\nTesting models:")
working = []
for model in candidates:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": '{"status": "ok", "model": "test"}'},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=50,
        )
        text = resp.choices[0].message.content
        result = json.loads(text)
        print(f"  [OK]  {model} -> {result}")
        working.append(model)
        time.sleep(0.3)
    except Exception as e:
        print(f"  [FAIL] {model}: {str(e)[:120]}")

print(f"\n=> Recommended: {working[0] if working else 'NONE'}")
