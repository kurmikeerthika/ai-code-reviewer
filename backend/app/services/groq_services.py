from groq import Groq
from app.core.config import settings
import os

client = Groq(
    api_key=settings.groq_api_key
)

def review_code(code: str):

    prompt = f"""
You are an expert AI code reviewer.

Review this code and provide:

1. Bugs
2. Improvements
3. Optimizations
4. Security issues
5. Best practices

Code:
{code}
"""

    completion = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL"),
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=1024
    )

    return completion.choices[0].message.content