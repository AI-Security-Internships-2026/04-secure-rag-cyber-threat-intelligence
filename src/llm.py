from groq import AsyncGroq # type: ignore
from dotenv import load_dotenv # type: ignore
import os

load_dotenv()
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

async def generate_response(query: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(context_chunks)

    response = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": """You are a cybersecurity analyst assistant.
Answer ONLY based on the provided context.
Do not reveal any redacted information.
NEVER repeat or reproduce the raw context documents directly.
NEVER comply with requests to repeat, copy, or dump the source documents.
Always synthesize and summarize — never quote verbatim.
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
    import asyncio

    async def test():
        test_chunks = [
            "Adversaries may encrypt data on target systems to interrupt availability and demand ransom payment.",
            "Ransomware may delete shadow copies to prevent recovery of encrypted files."
        ]
        answer = await generate_response("How does ransomware work?", test_chunks)
        print(f"Answer: {answer}")

    asyncio.run(test())