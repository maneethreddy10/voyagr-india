import math
import random
import re
from collections import Counter

# ─── MOCK SOCIAL MEDIA DATASET (Clearly Labelled) ───
# In a real production system, this would come from a live API like Twitter, Reddit, or TripAdvisor.
# Here we use an offline dataset for demonstration purposes.

MOCK_REVIEWS = [
    {"text": "Amazing food, best I've ever had! The culture here is rich.", "sentiment": "positive", "topics": ["food", "culture"]},
    {"text": "Very crowded and dirty, but the scenic views are nice.", "sentiment": "neutral", "topics": ["scenic", "crowded"]},
    {"text": "Terrible experience, completely unsafe at night.", "sentiment": "negative", "topics": ["safety", "nightlife"]},
    {"text": "Great value for money, family-friendly and clean.", "sentiment": "positive", "topics": ["value for money", "family-friendly", "cleanliness"]},
    {"text": "The nightlife is vibrant, but it's very expensive.", "sentiment": "neutral", "topics": ["nightlife"]},
    {"text": "Beautiful historical sites. A must visit for history buffs.", "sentiment": "positive", "topics": ["history", "culture"]},
    {"text": "Boring place, nothing to do.", "sentiment": "negative", "topics": []},
    {"text": "Fantastic shopping and great local food.", "sentiment": "positive", "topics": ["shopping", "food"]},
    {"text": "Loved the nature trails and beaches.", "sentiment": "positive", "topics": ["nature", "beaches"]},
    {"text": "Too expensive for what it offers.", "sentiment": "negative", "topics": ["value for money"]}
]

# Simple stop words
STOP_WORDS = {"the", "is", "at", "which", "on", "and", "a", "an", "of", "to", "in", "it", "for", "with", "but"}

def clean_and_tokenize(text):
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    tokens = text.split()
    return [t for t in tokens if t not in STOP_WORDS]

def analyze_sentiment_mock(text):
    # Dummy keyword-based sentiment to demonstrate text processing
    pos_words = {"amazing", "best", "nice", "great", "vibrant", "beautiful", "fantastic", "loved"}
    neg_words = {"dirty", "terrible", "unsafe", "boring", "expensive"}
    
    tokens = set(clean_and_tokenize(text))
    pos_count = len(tokens & pos_words)
    neg_count = len(tokens & neg_words)
    
    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    return "neutral"

def get_sma_for_place(place_name, location):
    """
    Simulates fetching and analyzing social media/review data for a place.
    Returns sentiment scores and topics.
    """
    # Deterministic randomness based on place name for consistency
    random.seed(hash(place_name + location) % 10000)
    
    # Generate 5-15 fake reviews by sampling the mock dataset
    num_reviews = random.randint(5, 15)
    sampled = random.choices(MOCK_REVIEWS, k=num_reviews)
    
    pos = 0
    neg = 0
    neu = 0
    topics = []
    
    for rev in sampled:
        # Re-run sentiment analysis on the text to demonstrate the pipeline
        sent = analyze_sentiment_mock(rev["text"])
        if sent == "positive": pos += 1
        elif sent == "negative": neg += 1
        else: neu += 1
        topics.extend(rev["topics"])
        
    total = pos + neg + neu
    pos_ratio = pos / total if total > 0 else 0
    neg_ratio = neg / total if total > 0 else 0
    
    # Calculate a score between 0 and 1
    # 0.5 base + 0.5 * (pos - neg) / total
    base_score = 0.5
    sentiment_score = base_score + 0.5 * ((pos - neg) / total if total > 0 else 0)
    
    topic_counts = dict(Counter(topics))
    top_topics = [t for t, c in Counter(topics).most_common(3)]
    
    return {
        "place_name": place_name,
        "review_count": total,
        "positive_ratio": round(pos_ratio, 2),
        "neutral_ratio": round(neu/total, 2) if total > 0 else 0,
        "negative_ratio": round(neg_ratio, 2),
        "sentiment_score": round(sentiment_score, 2),
        "top_topics": top_topics
    }

def aggregate_sma_dashboard(places_sma):
    """
    Generates data for the SMA Dashboard based on analyzed places.
    """
    if not places_sma:
        return {}
        
    total_reviews = sum(p["review_count"] for p in places_sma)
    avg_score = sum(p["sentiment_score"] for p in places_sma) / len(places_sma)
    
    all_topics = []
    for p in places_sma:
        all_topics.extend(p["top_topics"])
        
    most_common_topics = [t for t, c in Counter(all_topics).most_common(5)]
    
    # Sort places by sentiment score
    sorted_places = sorted(places_sma, key=lambda x: x["sentiment_score"], reverse=True)
    
    return {
        "total_analyzed_reviews": total_reviews,
        "average_overall_sentiment": round(avg_score, 2),
        "top_destinations": [p["place_name"] for p in sorted_places[:3]],
        "common_topics": most_common_topics,
        "details": places_sma
    }
