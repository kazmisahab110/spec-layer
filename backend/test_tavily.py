import os
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient


# Find the .env file in the project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    raise ValueError("TAVILY_API_KEY was not found in .env")

# Create Tavily client
tavily = TavilyClient(api_key=api_key)

# Test search
response = tavily.search(
    query="Dell computer monitor official manual troubleshooting components",
    max_results=5
)

print("\n=== TAVILY SEARCH RESULTS ===\n")

for result in response["results"]:
    print("TITLE:", result["title"])
    print("URL:", result["url"])
    print("CONTENT:", result["content"][:500])
    print("-" * 80)