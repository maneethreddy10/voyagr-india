import os
import json
import urllib.request
import urllib.parse
import urllib.error
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = Flask(__name__)
CORS(app)

GROQ_API_KEY         = os.getenv("GROQ_API_KEY")
OPENWEATHER_API_KEY  = os.getenv("OPENWEATHER_API_KEY")
FOURSQUARE_API_KEY   = os.getenv("FOURSQUARE_API_KEY")
EXCHANGERATE_API_KEY = os.getenv("EXCHANGERATE_API_KEY")
YELP_API_KEY         = os.getenv("YELP_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)


# ─── 1. OPENWEATHERMAP ────────────────────────────────────────────────────────

def get_live_weather(city):
    try:
        encoded = urllib.parse.quote(city)
        url = f"https://api.openweathermap.org/data/2.5/weather?q={encoded}&appid={OPENWEATHER_API_KEY}&units=metric"
        with urllib.request.urlopen(urllib.request.Request(url), timeout=10) as r:
            data = json.loads(r.read().decode())
        return {
            "success":     True,
            "temp_c":      round(data["main"]["temp"]),
            "feels_like":  round(data["main"]["feels_like"]),
            "humidity":    data["main"]["humidity"],
            "description": data["weather"][0]["description"].capitalize(),
            "wind_speed":  data["wind"]["speed"],
            "city":        data["name"],
            "country":     data["sys"]["country"],
        }
    except Exception as e:
        print(f"Weather error: {e}")
        return {"success": False}


# ─── 2. EXCHANGERATE ─────────────────────────────────────────────────────────

def get_exchange_rates():
    try:
        url = f"https://v6.exchangerate-api.com/v6/{EXCHANGERATE_API_KEY}/latest/INR"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read().decode())
        rates    = data.get("conversion_rates", {})
        usd_rate = rates.get("USD", 1)
        return {
            "success":    True,
            "usd_to_inr": round(1 / usd_rate, 2) if usd_rate else 83,
            "inr_to_usd": round(usd_rate, 6),
        }
    except Exception as e:
        print(f"ExchangeRate error: {e}")
        return {"success": False, "usd_to_inr": 83}


# ─── 3. FOURSQUARE ───────────────────────────────────────────────────────────

def search_foursquare(query, location, categories=None, limit=10):
    try:
        params = {"query": query, "near": location, "limit": limit, "sort": "RELEVANCE"}
        if categories:
            params["categories"] = categories
        url = "https://api.foursquare.com/v3/places/search?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={"Authorization": FOURSQUARE_API_KEY, "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        places = []
        for p in data.get("results", []):
            cats = p.get("categories", [])
            places.append({
                "name":       p.get("name", ""),
                "address":    p.get("location", {}).get("formatted_address", ""),
                "category":   cats[0].get("name", "") if cats else "",
                "maps_query": f"{p.get('name', '')} {location}",
            })
        return {"success": True, "places": places}
    except Exception as e:
        print(f"Foursquare error: {e}")
        return {"success": False, "places": []}


def get_foursquare_data(destination):
    results  = {}
    location = destination + ", India" if not any(c in destination.lower() for c in ["dubai","paris","tokyo","bali","london","singapore","bangkok","new york","sydney"]) else destination

    hotels = search_foursquare("hotel", location, categories="19014", limit=10)
    if hotels.get("success"):
        results["hotels"] = hotels["places"]
        print(f"Foursquare hotels: {len(hotels['places'])} found")

    attractions = search_foursquare("tourist attraction", location, categories="16000", limit=10)
    if attractions.get("success"):
        results["attractions"] = attractions["places"]
        print(f"Foursquare attractions: {len(attractions['places'])} found")

    transport = search_foursquare("transit station", location, limit=6)
    if transport.get("success"):
        results["transport"] = transport["places"]
        print(f"Foursquare transport: {len(transport['places'])} found")

    return results


# ─── 4. YELP ─────────────────────────────────────────────────────────────────

def get_yelp_restaurants(destination, dietary=None):
    try:
        term     = "restaurants"
        if dietary and dietary != "No restrictions":
            term = f"{dietary} restaurants"
        location = destination + ", India" if not any(c in destination.lower() for c in ["dubai","paris","tokyo","bali","london","singapore","bangkok","new york","sydney"]) else destination
        params   = {"term": term, "location": location, "limit": 15, "sort_by": "rating"}
        url      = "https://api.yelp.com/v3/businesses/search?" + urllib.parse.urlencode(params)
        req      = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {YELP_API_KEY}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        restaurants = []
        for b in data.get("businesses", []):
            cats = b.get("categories", [])
            restaurants.append({
                "name":         b.get("name", ""),
                "rating":       b.get("rating", ""),
                "review_count": b.get("review_count", 0),
                "price":        b.get("price", "$$"),
                "cuisine":      cats[0].get("title", "") if cats else "",
                "address":      " ".join(b.get("location", {}).get("display_address", [])),
                "maps_query":   f"{b.get('name', '')} {destination} restaurant",
            })
        return {"success": True, "restaurants": restaurants}
    except Exception as e:
        print(f"Yelp error: {e}")
        return {"success": False, "restaurants": []}


# ─── 5. GROQ PROMPT ──────────────────────────────────────────────────────────

def build_prompt(data, weather_info=None, exchange_info=None, foursquare_data=None, yelp_data=None):
    destination   = data.get("destination", "")
    days          = data.get("days", "7")
    travelers     = data.get("travelers", "2")
    budget_inr    = data.get("budget", "50000")
    travel_date   = data.get("travelDate", "any time")
    style         = data.get("style", "Relaxed Explorer")
    interests     = data.get("interests", "Sightseeing")
    dietary       = data.get("dietary", "No restrictions")
    accommodation = data.get("accommodation", "Hotel")
    departure     = data.get("departureCity", "Mumbai")
    trip_type     = data.get("tripType", "International")

    usd_to_inr = exchange_info.get("usd_to_inr", 83) if exchange_info and exchange_info.get("success") else 83
    try:
        budget_num = int(str(budget_inr).replace(",","").replace("INR","").replace("Rs","").replace("₹","").strip())
    except:
        budget_num = 50000
    budget_usd = round(budget_num / usd_to_inr)

    weather_ctx = ""
    if weather_info and weather_info.get("success"):
        weather_ctx = f"""
LIVE WEATHER in {destination} right now:
- Temperature: {weather_info['temp_c']}C (feels like {weather_info['feels_like']}C)
- Conditions: {weather_info['description']}
- Humidity: {weather_info['humidity']}%
- Wind: {weather_info['wind_speed']} m/s
Use this in your weather_advisory field.
"""

    exchange_ctx = ""
    if exchange_info and exchange_info.get("success"):
        exchange_ctx = f"""
LIVE EXCHANGE RATE: 1 USD = INR {usd_to_inr}
Budget: INR {budget_inr} = approx USD {budget_usd}
ALL prices must be in INR only.
"""

    hotel_ctx = ""
    if foursquare_data and foursquare_data.get("hotels"):
        names = [h["name"] for h in foursquare_data["hotels"]]
        hotel_ctx = f"VERIFIED HOTELS from Foursquare in {destination} ({len(names)} found):\n{', '.join(names)}\nPrioritize these real hotel names in your hotels section."

    attraction_ctx = ""
    if foursquare_data and foursquare_data.get("attractions"):
        names = [a["name"] for a in foursquare_data["attractions"]]
        attraction_ctx = f"VERIFIED ATTRACTIONS from Foursquare in {destination} ({len(names)} found):\n{', '.join(names)}\nInclude these in your itinerary."

    transport_ctx = ""
    if foursquare_data and foursquare_data.get("transport"):
        names = [t["name"] for t in foursquare_data["transport"]]
        transport_ctx = f"VERIFIED TRANSPORT from Foursquare in {destination}:\n{', '.join(names)}"

    restaurant_ctx = ""
    if yelp_data and yelp_data.get("restaurants"):
        rest_list = [f"{r['name']} (Rating:{r['rating']}/5, {r['cuisine']}, {r['price']})" for r in yelp_data["restaurants"]]
        restaurant_ctx = f"VERIFIED RESTAURANTS from Yelp in {destination} ({len(rest_list)} found):\n" + "\n".join(rest_list) + "\nUse these real restaurants."

    return f"""You are an elite Indian travel planner helping Indian travelers plan trips from India.
ALL prices MUST be in Indian Rupees (INR). Never use USD for prices.

CRITICAL RULES — MUST FOLLOW:
1. Generate a COMPLETE itinerary for ALL {days} days. Every day from Day 1 to Day {days} must have at least 4 activities.
2. Generate AT LEAST 6 hotels (2 Luxury, 2 Mid-range, 2 Budget)
3. Generate AT LEAST 10 restaurants with variety
4. Generate AT LEAST 6 transport options
5. ALL prices in INR only
6. Every hotel, restaurant, attraction must be REAL and currently operating
7. Prioritize verified Foursquare and Yelp places listed below
8. No placeholder names ever

Trip details:
- Destination: {destination}
- Duration: {days} days (GENERATE ALL {days} DAYS)
- Travelers: {travelers} people
- Total Budget: INR {budget_inr} (approx USD {budget_usd})
- Travel Period: {travel_date}
- Travel Style: {style}
- Interests: {interests}
- Dietary: {dietary}
- Accommodation: {accommodation}
- Departing from: {departure}, India
- Trip Type: {trip_type}

{weather_ctx}
{exchange_ctx}
{hotel_ctx}
{attraction_ctx}
{transport_ctx}
{restaurant_ctx}

Respond ONLY with a valid JSON object. No markdown, no backticks, just raw JSON:

{{
  "destination": "City, Country",
  "tagline": "Short poetic tagline max 10 words",
  "days": {days},
  "travelers": {travelers},
  "budget_inr": "{budget_inr}",
  "budget_usd_approx": "{budget_usd}",
  "travel_season": "Season + weather for {travel_date}",
  "weather_advisory": "Detailed weather advice using live data",
  "visa_info": "Visa requirements for Indian passport holders",
  "currency_info": "Local currency + live INR exchange rate",
  "flight_info": "Flights from {departure} to {destination} - airlines, duration, approx INR cost",
  "best_areas": [
    {{"name": "Area 1", "vibe": "Description", "good_for": "Traveler type"}},
    {{"name": "Area 2", "vibe": "Description", "good_for": "Traveler type"}},
    {{"name": "Area 3", "vibe": "Description", "good_for": "Traveler type"}}
  ],
  "itinerary": [
    {{
      "day": 1,
      "theme": "Arrival & First Impressions",
      "activities": [
        {{"time": "09:00", "name": "Real attraction", "note": "Details + insider tip", "duration": "2 hours", "cost_inr": "INR 500 per person", "maps_query": "attraction name city"}},
        {{"time": "12:00", "name": "Lunch spot", "note": "Details", "duration": "1 hour", "cost_inr": "INR 400 per person", "maps_query": "restaurant name city"}},
        {{"time": "14:00", "name": "Afternoon activity", "note": "Details", "duration": "2 hours", "cost_inr": "INR 300 per person", "maps_query": "place name city"}},
        {{"time": "18:00", "name": "Evening activity", "note": "Details", "duration": "2 hours", "cost_inr": "INR 200 per person", "maps_query": "place name city"}}
      ]
    }}
  ],
  "hotels": [
    {{"tier": "Luxury", "name": "Real hotel 1", "area": "District", "why": "Why great", "highlights": ["H1","H2","H3"], "price_per_night_inr": "INR 15000", "rating": "4.8", "booking_tip": "Book on MakeMyTrip", "maps_query": "hotel name city"}},
    {{"tier": "Luxury", "name": "Real hotel 2", "area": "District", "why": "Why great", "highlights": ["H1","H2","H3"], "price_per_night_inr": "INR 12000", "rating": "4.6", "booking_tip": "Book on Booking.com", "maps_query": "hotel name city"}},
    {{"tier": "Mid-range", "name": "Real hotel 3", "area": "District", "why": "Why great", "highlights": ["H1","H2"], "price_per_night_inr": "INR 6000", "rating": "4.3", "booking_tip": "Check OYO or MakeMyTrip", "maps_query": "hotel name city"}},
    {{"tier": "Mid-range", "name": "Real hotel 4", "area": "District", "why": "Why great", "highlights": ["H1","H2"], "price_per_night_inr": "INR 4500", "rating": "4.1", "booking_tip": "Book in advance", "maps_query": "hotel name city"}},
    {{"tier": "Budget", "name": "Real hotel 5", "area": "District", "why": "Why great", "highlights": ["H1","H2"], "price_per_night_inr": "INR 2500", "rating": "4.0", "booking_tip": "Check Hostelworld", "maps_query": "hotel name city"}},
    {{"tier": "Budget", "name": "Real hotel 6", "area": "District", "why": "Why great", "highlights": ["H1","H2"], "price_per_night_inr": "INR 1500", "rating": "3.8", "booking_tip": "Book on OYO", "maps_query": "hotel name city"}}
  ],
  "restaurants": [
    {{"name": "Restaurant 1", "cuisine": "Type", "dish": "Must-try dish", "why": "Why special", "price_range_inr": "INR 800-1500", "yelp_rating": "4.5", "meal_type": "Dinner", "dietary_note": "Info", "maps_query": "restaurant city"}},
    {{"name": "Restaurant 2", "cuisine": "Type", "dish": "Must-try dish", "why": "Why special", "price_range_inr": "INR 500-1000", "yelp_rating": "4.3", "meal_type": "Lunch", "dietary_note": "Info", "maps_query": "restaurant city"}},
    {{"name": "Restaurant 3", "cuisine": "Type", "dish": "Must-try dish", "why": "Why special", "price_range_inr": "INR 300-600", "yelp_rating": "4.2", "meal_type": "Breakfast", "dietary_note": "Info", "maps_query": "restaurant city"}},
    {{"name": "Restaurant 4", "cuisine": "Type", "dish": "Must-try dish", "why": "Why special", "price_range_inr": "INR 1000-2000", "yelp_rating": "4.6", "meal_type": "Dinner", "dietary_note": "Info", "maps_query": "restaurant city"}},
    {{"name": "Restaurant 5", "cuisine": "Type", "dish": "Must-try dish", "why": "Why special", "price_range_inr": "INR 400-800", "yelp_rating": "4.1", "meal_type": "All-day", "dietary_note": "Info", "maps_query": "restaurant city"}},
    {{"name": "Restaurant 6", "cuisine": "Type", "dish": "Must-try dish", "why": "Why special", "price_range_inr": "INR 600-1200", "yelp_rating": "4.4", "meal_type": "Lunch", "dietary_note": "Info", "maps_query": "restaurant city"}},
    {{"name": "Restaurant 7", "cuisine": "Type", "dish": "Must-try dish", "why": "Why special", "price_range_inr": "INR 200-500", "yelp_rating": "4.0", "meal_type": "Breakfast", "dietary_note": "Info", "maps_query": "restaurant city"}},
    {{"name": "Restaurant 8", "cuisine": "Type", "dish": "Must-try dish", "why": "Why special", "price_range_inr": "INR 1500-3000", "yelp_rating": "4.7", "meal_type": "Dinner", "dietary_note": "Info", "maps_query": "restaurant city"}},
    {{"name": "Restaurant 9", "cuisine": "Type", "dish": "Must-try dish", "why": "Why special", "price_range_inr": "INR 300-700", "yelp_rating": "4.2", "meal_type": "All-day", "dietary_note": "Info", "maps_query": "restaurant city"}},
    {{"name": "Restaurant 10", "cuisine": "Type", "dish": "Must-try dish", "why": "Why special", "price_range_inr": "INR 700-1400", "yelp_rating": "4.3", "meal_type": "Lunch", "dietary_note": "Info", "maps_query": "restaurant city"}}
  ],
  "transport": [
    {{"type": "Airport Transfer", "name": "Real service", "description": "How to use", "from_airport": true, "cost_inr": "INR 500", "tip": "Insider tip", "maps_query": "transport city"}},
    {{"type": "Metro/Train", "name": "Real service", "description": "How to use", "from_airport": false, "cost_inr": "INR 50", "tip": "Insider tip", "maps_query": "metro station city"}},
    {{"type": "Bus", "name": "Real service", "description": "How to use", "from_airport": false, "cost_inr": "INR 30", "tip": "Insider tip", "maps_query": "bus stand city"}},
    {{"type": "Auto Rickshaw", "name": "Local autos", "description": "How to use", "from_airport": false, "cost_inr": "INR 100-200", "tip": "Always use meter", "maps_query": "auto stand city"}},
    {{"type": "Taxi/Cab", "name": "Real service like Ola/Uber", "description": "How to use", "from_airport": true, "cost_inr": "INR 300-600", "tip": "Book in advance", "maps_query": "taxi city"}},
    {{"type": "Rental", "name": "Real rental service", "description": "How to use", "from_airport": false, "cost_inr": "INR 800-1500/day", "tip": "Bring license", "maps_query": "car rental city"}}
  ],
  "day_trips": [
    {{"name": "Nearby destination 1", "distance": "XX km", "how_to_get": "Transport + time", "why_go": "Why worth it", "best_for": "Traveler type"}},
    {{"name": "Nearby destination 2", "distance": "XX km", "how_to_get": "Transport + time", "why_go": "Why worth it", "best_for": "Traveler type"}},
    {{"name": "Nearby destination 3", "distance": "XX km", "how_to_get": "Transport + time", "why_go": "Why worth it", "best_for": "Traveler type"}}
  ],
  "budget_breakdown_inr": {{
    "flights_from_india": 0,
    "accommodation": 0,
    "food": 0,
    "transport": 0,
    "activities": 0,
    "shopping": 0,
    "buffer": 0
  }},
  "money_tips": ["Tip 1", "Tip 2", "Tip 3", "Tip 4", "Tip 5"],
  "india_specific_tips": ["Tip 1", "Tip 2", "Tip 3", "Tip 4", "Tip 5"],
  "packing_list": {{
    "essentials": ["item1","item2","item3","item4"],
    "clothing":   ["item1","item2","item3"],
    "tech":       ["item1","item2"],
    "health":     ["item1","item2","item3"],
    "documents":  ["Indian Passport","Visa","Travel insurance","Forex card","Booking confirmations"]
  }},
  "local_tips": ["Tip 1","Tip 2","Tip 3","Tip 4","Tip 5"],
  "phrases": [
    {{"original": "Hello",       "local": "Local word", "pronunciation": "how to say"}},
    {{"original": "Thank you",   "local": "Local word", "pronunciation": "how to say"}},
    {{"original": "How much?",   "local": "Local word", "pronunciation": "how to say"}},
    {{"original": "Where is?",   "local": "Local word", "pronunciation": "how to say"}},
    {{"original": "Help!",       "local": "Local word", "pronunciation": "how to say"}}
  ],
  "emergency": {{
    "police":           "Local number",
    "ambulance":        "Local number",
    "fire":             "Local number",
    "indian_embassy":   "Indian Embassy in {destination}",
    "tourist_helpline": "Tourist helpline number"
  }}
}}"""


# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    try:
        if not GROQ_API_KEY:
            return jsonify({"error": "GROQ_API_KEY not found in .env file"}), 500

        data        = request.get_json()
        if not data.get("destination"):
            return jsonify({"error": "Destination is required"}), 400

        destination = data.get("destination", "")
        dietary     = data.get("dietary", "No restrictions")

        # 1. Live weather
        weather_info = None
        if OPENWEATHER_API_KEY:
            print(f"Fetching weather for {destination}...")
            weather_info = get_live_weather(destination)
            print(f"Weather: {weather_info.get('temp_c')}C, {weather_info.get('description')}" if weather_info.get("success") else "Weather failed")

        # 2. Exchange rates
        exchange_info = None
        if EXCHANGERATE_API_KEY:
            print("Fetching INR exchange rates...")
            exchange_info = get_exchange_rates()
            print(f"1 USD = INR {exchange_info.get('usd_to_inr')}" if exchange_info.get("success") else "Exchange failed")

        # 3. Foursquare
        foursquare_data = None
        if FOURSQUARE_API_KEY:
            print(f"Fetching Foursquare places for {destination}...")
            foursquare_data = get_foursquare_data(destination)

        # 4. Yelp
        yelp_data = None
        if YELP_API_KEY:
            print(f"Fetching Yelp restaurants for {destination}...")
            yelp_data = get_yelp_restaurants(destination, dietary)
            print(f"Yelp: {len(yelp_data.get('restaurants',[]))} found" if yelp_data.get("success") else "Yelp failed")

        # 5. Groq
        prompt = build_prompt(data, weather_info, exchange_info, foursquare_data, yelp_data)
        print(f"Calling Groq AI for {data.get('days')} day trip to {destination}...")

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=32768,
            temperature=0.7
        )

        raw  = response.choices[0].message.content.strip()
        raw  = raw.replace("```json", "").replace("```", "").strip()
        plan = json.loads(raw)

        # Attach live data
        if weather_info and weather_info.get("success"):
            plan["live_weather"] = weather_info
        if exchange_info and exchange_info.get("success"):
            plan["live_exchange"] = exchange_info
        if yelp_data and yelp_data.get("success"):
            plan["yelp_restaurants"] = yelp_data["restaurants"]
        if foursquare_data:
            plan["foursquare_places"] = foursquare_data

        days_generated = len(plan.get("itinerary", []))
        hotels_gen     = len(plan.get("hotels", []))
        restaurants_gen= len(plan.get("restaurants", []))
        transport_gen  = len(plan.get("transport", []))
        print(f"Generated: {days_generated} days | {hotels_gen} hotels | {restaurants_gen} restaurants | {transport_gen} transport options")

        return jsonify({"success": True, "plan": plan})

    except json.JSONDecodeError as e:
        return jsonify({"error": f"Failed to parse AI response: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    print(f"\n🇮🇳 Voyagr India — Trip Planner running on http://localhost:{port}")
    print(f"Groq:         {'YES' if GROQ_API_KEY         else 'NOT FOUND'}")
    print(f"OpenWeather:  {'YES' if OPENWEATHER_API_KEY  else 'NOT FOUND'}")
    print(f"Foursquare:   {'YES' if FOURSQUARE_API_KEY   else 'NOT FOUND'}")
    print(f"ExchangeRate: {'YES' if EXCHANGERATE_API_KEY else 'NOT FOUND'}")
    print(f"Yelp:         {'YES' if YELP_API_KEY         else 'NOT FOUND'}\n")
    app.run(debug=debug, port=port)