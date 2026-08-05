"""Script to list all available models for this API key."""
from dotenv import load_dotenv
load_dotenv()
import os
from google import genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("ERROR: No GEMINI_API_KEY found in .env")
    exit(1)

print(f"API Key: {api_key[:12]}...")

client = genai.Client(api_key=api_key)

print("\nAvailable models:")
try:
    for model in client.models.list():
        name = model.name
        # Only show generative models
        if "gemini" in name.lower():
            print(f"  - {name}")
except Exception as e:
    print(f"Error listing models: {e}")
