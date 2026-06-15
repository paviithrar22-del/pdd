import asyncio
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup minimal logging to see outputs clearly
logging.basicConfig(level=logging.INFO)

from app.services.moderation_service import classify_text
from app.services.analysis_pipeline import analyze_content
from app.services.severity_service import calculate_severity

test_cases = [
    "I love this post, great job!",
    "You are so stupid and ugly, delete your account.",
    "I will find you and hurt you.",
    "This is garbage.",
    "Please check out my new reel!",
    "stfu you idiot",
    "Nobody likes you, kill yourself",
    "kys",
    "I'm going to blow up your house",
    "What a great day to be alive",
]

def run_tests():
    print("--- Testing classify_text ---")
    for text in test_cases:
        res = classify_text(text)
        print(f"Text: '{text}'")
        print(f"Result: {res}")
        print("-" * 40)

if __name__ == "__main__":
    run_tests()
