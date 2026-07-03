"""Catalyst Scorer (25% weightage).

Uses raw data from catalyst_data.py to compute 0-25 points.
"""
from .catalyst_data import fetch_news_tone, fetch_reddit_pulse

def score_catalyst(symbol: str) -> int:
    news = fetch_news_tone(symbol)
    reddit = fetch_reddit_pulse(symbol)
    
    score = 0
    # Add news/sentiment logic
    if news.score > 0: score += 5
    if reddit.score > 0: score += 5
    
    return min(25, score)
