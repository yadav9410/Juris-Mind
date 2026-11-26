
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load configuration from the project-root .env file.
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv(
    "OPENAI_BASE_URL",
    "https://api.groq.com/openai/v1"
)
model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is missing from .env")

# Connect using the OpenAI-compatible Groq endpoint.
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
    timeout=60,
)

print("Testing Groq connection...")
print("Model:", model)

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: JurisMind Groq connection successful."
            }
        ],
        max_completion_tokens=100,
    )

    print("\nSUCCESS!")
    print("Model response:")
    print(response.choices[0].message.content)

    if response.usage:
        print("\nToken usage:")
        print("Input:", response.usage.prompt_tokens)
        print("Output:", response.usage.completion_tokens)
        print("Total:", response.usage.total_tokens)

except Exception as exc:
    print("\nGroq connection failed.")
    print("Error type:", type(exc).__name__)
    print("Error:", str(exc))
