from groq import Groq  # type: ignore[import]
from dotenv import load_dotenv
import os

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_response(query: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(context_chunks)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": """You are a cybersecurity analyst assistant.
Answer ONLY based on the provided context.
Do not reveal any redacted information.
If context is insufficient, say so clearly."""
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}"
            }
        ],
        max_tokens=500,
        temperature=0.3
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    test_chunks = [
        "Adversaries may encrypt data on target systems to interrupt availability and demand ransom payment.",
        "Ransomware may delete shadow copies to prevent recovery of encrypted files."
    ]
    answer = generate_response("How does ransomware work?", test_chunks)
    print(f"Answer: {answer}")