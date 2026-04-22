import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SCRIPT_PROMPT = """You are a viral YouTube Shorts scriptwriter specializing in money and finance tips.
Write punchy, engaging scripts that hook viewers in the first 3 seconds.
Rules:
- Max 60 seconds when read aloud (~120-140 words)
- Start with a shocking hook (e.g. "Most people will never be rich because...")
- Use simple language, short sentences
- End with a call to action ("Follow for more money tips")
- Return ONLY the spoken script text, no labels, no stage directions
"""

QUERY_PROMPT = """You are a Pexels video search expert.
Given a YouTube Shorts topic, return a 2-4 word Pexels search query that finds
cinematic portrait/vertical footage visually matching the topic's mood.
Return ONLY the search query — no explanation, no quotes, no punctuation.
Examples:
  topic: "why 99% of people stay broke"   -> dark city rain
  topic: "morning habits of millionaires" -> luxury morning lifestyle
  topic: "crypto investing for beginners" -> digital neon technology
"""


def generate_script(topic: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        config=types.GenerateContentConfig(system_instruction=SCRIPT_PROMPT),
        contents=f"Write a YouTube Shorts script about: {topic}",
    )
    return response.text.strip()


def generate_pexels_query(topic: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        config=types.GenerateContentConfig(system_instruction=QUERY_PROMPT),
        contents=f"Topic: {topic}",
    )
    return response.text.strip()


def _keyword_fallback(topic: str) -> str:
    """Extract visual keywords from topic when Gemini is unavailable."""
    stopwords = {"why","how","the","a","an","is","are","do","does","can","will",
                 "to","of","in","on","for","and","or","but","not","that","this",
                 "with","your","you","i","my","we","they","it","be","been","has",
                 "have","from","at","by","as","so","if","get","make","what","who",
                 "most","all","just","more","no","yes","very","too","also","even",
                 "people","person","everyone","nobody","still","stay","keep"}
    words = [w.lower().strip(".,!?") for w in topic.split()]
    keywords = [w for w in words if w not in stopwords and len(w) > 2]
    query = " ".join(keywords[:3]) if keywords else "cinematic city"
    return query


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="money habit most people ignore")
    args = parser.parse_args()

    print("\n--- PEXELS QUERY ---")
    print(generate_pexels_query(args.topic))
    print("\n--- GENERATED SCRIPT ---\n")
    print(generate_script(args.topic))
    print("\n------------------------")
