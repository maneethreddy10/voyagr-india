import json
import os
import math
from collections import defaultdict
from services.sma import get_sma_for_place

# ─── INTERACTION DATABASE (Local File for Demo) ───
DB_FILE = 'interactions.json'

# MOCK SEED DATA: Showing item-item relationships
# This represents past users interacting with items.
# We will use this to build an item-item similarity matrix.
MOCK_INTERACTIONS = [
    {"user": "u1", "item": "Tokyo Skytree", "type": "like", "weight": 5},
    {"user": "u1", "item": "Shibuya Sky", "type": "view", "weight": 1},
    {"user": "u1", "item": "TeamLab", "type": "save", "weight": 4},
    {"user": "u2", "item": "Meiji Shrine", "type": "like", "weight": 5},
    {"user": "u2", "item": "Senso-ji", "type": "like", "weight": 5},
    {"user": "u3", "item": "TeamLab", "type": "like", "weight": 5},
    {"user": "u3", "item": "Shibuya Sky", "type": "like", "weight": 5},
    {"user": "u3", "item": "Tokyo Skytree", "type": "view", "weight": 1},
]

WEIGHTS = {
    "view": 1,
    "click": 2,
    "save": 4,
    "like": 5,
    "dislike": -2
}

def load_interactions():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump(MOCK_INTERACTIONS, f)
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def save_interaction(user_id, item_name, interaction_type):
    data = load_interactions()
    weight = WEIGHTS.get(interaction_type, 1)
    data.append({"user": user_id, "item": item_name, "type": interaction_type, "weight": weight})
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)
        
def get_user_interactions(user_id):
    data = load_interactions()
    user_data = defaultdict(int)
    for row in data:
        if row["user"] == user_id:
            user_data[row["item"]] += row["weight"]
    return user_data

# ─── TF-IDF / COSINE SIMILARITY (Content-Based) ───
def cosine_similarity(vec1, vec2):
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])
    
    sum1 = sum([vec1[x]**2 for x in vec1.keys()])
    sum2 = sum([vec2[x]**2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    
    if not denominator:
        return 0.0
    return float(numerator) / denominator

def get_content_vector(text):
    words = text.lower().replace(',', ' ').split()
    vec = Counter(words)
    return vec

# ─── ITEM-BASED COLLABORATIVE FILTERING ───
def build_item_similarity_matrix():
    data = load_interactions()
    # Build user-item matrix
    user_item = defaultdict(dict)
    for row in data:
        user_item[row["user"]][row["item"]] = user_item[row["user"]].get(row["item"], 0) + row["weight"]
        
    # Transpose to item-user matrix
    item_user = defaultdict(dict)
    for u, items in user_item.items():
        for i, w in items.items():
            item_user[i][u] = w
            
    # Calculate item-item similarities
    items = list(item_user.keys())
    similarity_matrix = defaultdict(dict)
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            item1 = items[i]
            item2 = items[j]
            sim = cosine_similarity(item_user[item1], item_user[item2])
            if sim > 0:
                similarity_matrix[item1][item2] = sim
                similarity_matrix[item2][item1] = sim
                
    return similarity_matrix

def get_item_cf_score(candidate_name, user_interactions, item_sim_matrix):
    score = 0
    total_sim = 0
    for hist_item, hist_weight in user_interactions.items():
        if hist_weight <= 0: continue
        sim = item_sim_matrix.get(candidate_name, {}).get(hist_item, 0)
        if sim > 0:
            score += sim * hist_weight
            total_sim += sim
    
    if total_sim == 0:
        return 0
    return min(1.0, score / (total_sim * 5)) # Normalize roughly to 0-1

# ─── CONFIGURABLE WEIGHTS ───
HYBRID_WEIGHTS_NEW_USER = {
    "content": 0.50,
    "social": 0.25,
    "popularity": 0.25,
    "cf": 0.0
}

HYBRID_WEIGHTS_EXISTING_USER = {
    "content": 0.35,
    "cf": 0.35,
    "social": 0.20,
    "popularity": 0.10
}

# ─── MAIN RECOMMENDER FUNCTION ───
def recommend_places(places_data, user_profile, item_type="attraction"):
    """
    Ranks a list of places based on Hybrid Recommendation.
    places_data: list of dicts from Foursquare/Geoapify
    user_profile: dict with interests, budget, etc.
    """
    user_id = user_profile.get("user_id", "anonymous")
    user_interests_str = user_profile.get("interests", "")
    user_vec = get_content_vector(user_interests_str)
    
    user_interactions = get_user_interactions(user_id)
    is_new_user = len(user_interactions) == 0
    weights = HYBRID_WEIGHTS_NEW_USER if is_new_user else HYBRID_WEIGHTS_EXISTING_USER
    
    item_sim_matrix = build_item_similarity_matrix()
    
    ranked_results = []
    sma_data_list = []
    
    for place in places_data:
        name = place.get("name", "")
        category = place.get("category", place.get("cuisine", ""))
        desc = name + " " + category
        
        # 1. Content-Based Score
        place_vec = get_content_vector(desc)
        content_score = cosine_similarity(user_vec, place_vec)
        
        # 2. Collaborative Filtering Score
        cf_score = get_item_cf_score(name, user_interactions, item_sim_matrix)
        
        # 3. Social Media Score
        location = user_profile.get("destination", "")
        sma = get_sma_for_place(name, location)
        sma_data_list.append(sma)
        social_score = sma["sentiment_score"]
        
        # 4. Popularity Score (Mocked or from Geoapify review count)
        rev_count = place.get("review_count", sma["review_count"])
        # Normalize popularity logaritmically
        popularity_score = min(1.0, math.log1p(rev_count) / math.log1p(1000))
        
        # 5. Hybrid Score
        final_score = (
            weights["content"] * content_score +
            weights["cf"] * cf_score +
            weights["social"] * social_score +
            weights["popularity"] * popularity_score
        )
        
        # Explaination
        explanation = []
        if content_score > 0.4:
            explanation.append("Matches your interests")
        if cf_score > 0.4:
            explanation.append("Similar to places you liked")
        if social_score > 0.7:
            explanation.append("High positive reviews")
            
        if not explanation:
            explanation.append("Popular in this area")
            
        place["rs_scores"] = {
            "content": round(content_score, 2),
            "cf": round(cf_score, 2),
            "social": round(social_score, 2),
            "popularity": round(popularity_score, 2),
            "final": round(final_score, 2),
            "explanation": " • ".join(explanation)
        }
        
        ranked_results.append(place)
        
    # Sort by final score descending
    ranked_results.sort(key=lambda x: x["rs_scores"]["final"], reverse=True)
    
    return ranked_results, sma_data_list
