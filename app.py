from flask import Flask, request, jsonify, render_template, send_from_directory, redirect
import os
import json
from google.generativeai import GenerativeModel
import google.generativeai as genai
import dotenv
import requests
import random



# Load environment variables from .env file
dotenv.load_dotenv()

# Configure the Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
GMAPS_API_KEY = os.getenv("GMAPS_API_KEY")



app = Flask(__name__, static_folder='static', template_folder='templates')

# Initialize the model
model = genai.GenerativeModel('models/gemini-2.0-flash')

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/plan-trip')
def plan_trip_page():
    return render_template('planTrip.html')

@app.route('/trip-results')
def trip_results_page():
    return render_template('tripResults.html')

@app.route('/api/plan-trip', methods=['POST'])
def plan_trip_api():
    try:
        # Get form data from request
        form_data = request.json

        # Validate required fields
        if not form_data.get('destination') or not form_data.get('tripDates'):
            return jsonify({
                "success": False,
                "error": "Destination and trip dates are required"
            }), 400

        # Format dates for better readability
        try:
            dates = form_data.get('tripDates', '').split(' to ')
            formatted_dates = dates[0]
            if len(dates) > 1:
                formatted_dates += " to " + dates[1]
        except:
            formatted_dates = form_data.get('tripDates', '')

        # Prepare prompt for Gemini
        prompt = f"""
        Plan a detailed trip to {form_data['destination']} with the following details:
        - Trip Dates: {formatted_dates}
        - Accommodation Type: {form_data.get('accommodation', 'Not specified')}
        - Number of Travelers: {form_data.get('travelers', 'Not specified')}
        - Budget Range: {form_data.get('budget', 'Not specified')}
        - Travel Pace: {form_data.get('pace', 'Not specified')}
        - Activities & Interests: {form_data.get('activities', 'Not specified')}
        - Special Requirements: {form_data.get('notes', 'Not specified')}

        Provide a detailed day-by-day itinerary, including:
        1. Recommended activities for each day based on the travel pace
        2. Suggested restaurants or food options appropriate for the budget
        3. Transportation tips
        4. Accommodation recommendations
        5. Any additional recommendations based on the user's preferences
        
        The response should be formatted in markdown with appropriate sections and formatting.
        """

        # Get response from Gemini
        response = model.generate_content(prompt)

        # Return the generated plan
        return jsonify({
            "success": True,
            "destination": form_data['destination'],
            "tripDates": formatted_dates,
            "accommodation": form_data.get('accommodation', 'Not specified'),
            "travelers": form_data.get('travelers', 'Not specified'),
            "budget": form_data.get('budget', 'Not specified'),
            "pace": form_data.get('pace', 'Not specified'),
            "activities": form_data.get('activities', 'Not specified'),
            "notes": form_data.get('notes', 'Not specified'),
            "generatedPlan": response.text
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/recommendations')
def recommendations():
    return render_template('recommendations.html')

@app.route('/destination')
def destination_details():
    destination_name = request.args.get('name')
    # Logic to fetch details for the specific destination
    return render_template('destination.html', destination=destination_name)

@app.route('/api/get-recommendations', methods=['POST'])
def get_travel_recommendations():
    try:
        # Get form data from request
        form_data = request.json
        
        # Prepare prompt for Gemini
        prompt = generate_recommendation_prompt(form_data)
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the response
        recommendations = parse_gemini_response(response.text)
        
        return jsonify({
            "success": True,
            "recommendations": recommendations
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def generate_recommendation_prompt(form_data):
    """Generate a prompt for Gemini based on user preferences"""
    # Extract values from form_data dictionary
    region = form_data.get('region', '')
    country = form_data.get('country', '')
    travel_type = form_data.get('travel-type', '')
    group_size = form_data.get('group-size', '')
    budget = form_data.get('budget', '')
    duration = form_data.get('duration', '')
    travel_date = form_data.get('travel-date', '')
    destination_type = form_data.get('destination-type', '')
    interests = form_data.get('interests', [])
    accommodation = form_data.get('accommodation-type', '')
    travel_pace = form_data.get('travel-pace', '')
    climate = form_data.get('climate', '')
    
    # Build the prompt with properly escaped JSON template
    prompt = f"""
    Based on the following travel preferences, please provide 3 suitable travel destinations with details:
    
    Region: {region}
    {"Country: " + country if country else ""}
    Travel Type: {travel_type}
    Number of Travelers: {group_size}
    Budget: ${budget}
    Trip Duration: {duration} days
    Travel Date: {travel_date}
    Destination Type: {destination_type}
    Interests: {', '.join(interests) if interests else 'Not specified'}
    Accommodation: {accommodation}
    Travel Pace: {travel_pace}
    Climate Preference: {climate}
    
    For each destination, please provide:
    1. Name of the destination
    2. Brief description
    3. Top 3 attractions
    4. Estimated daily budget
    5. Best time to visit
    6. Travel tips
    
    Format your response as JSON with the following structure:
    {{
      "destinations": [
        {{
          "name": "",
          "description": "",
          "attractions": ["", "", ""],
          "daily_budget": "",
          "best_time": "",
          "tips": ""
        }},
        ...
      ]
    }}
    """
    
    return prompt

def parse_gemini_response(response_text):
    """Extract and parse JSON from Gemini's response"""
    try:
        # Find JSON in the response (Gemini might wrap it in text)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            # If no JSON found, create a structured response from text
            return {
                "destinations": [{
                    "name": "Error parsing response",
                    "description": response_text[:500] + "...",
                    "attractions": [],
                    "daily_budget": "N/A",
                    "best_time": "N/A",
                    "tips": "Please try again with different preferences."
                }]
            }
    except json.JSONDecodeError:
        # If JSON is invalid, return error
        return {
            "destinations": [{
                "name": "Error parsing response",
                "description": "Unable to parse the AI response into proper format.",
                "attractions": [],
                "daily_budget": "N/A",
                "best_time": "N/A",
                "tips": "Please try again with different preferences."
            }]
        }
    
# New route to proxy Google Maps API JavaScript
@app.route('/api/gmaps-js')
def gmaps_js():
    return redirect(f"https://maps.googleapis.com/maps/api/js?key={GMAPS_API_KEY}&libraries=places&callback=initMap")

# New route to get place details from Google Maps API
@app.route('/api/place-details')
def get_place_details():
    try:
        place_name = request.args.get('name')
        if not place_name:
            return jsonify({"success": False, "error": "No place name provided"}), 400
        
        # First, use Places API to search for the place
        search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        search_params = {
            "input": place_name,
            "inputtype": "textquery",
            "fields": "place_id,name,formatted_address,geometry",
            "key": GMAPS_API_KEY
        }
        
        search_response = requests.get(search_url, params=search_params)
        search_data = search_response.json()
        
        if search_data.get("status") != "OK" or not search_data.get("candidates"):
            return jsonify({
                "success": False, 
                "error": f"Place not found: {search_data.get('status', 'Unknown error')}"
            }), 404
        
        place_id = search_data["candidates"][0]["place_id"]
        
        # Then, get detailed information about the place
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "name,formatted_address,formatted_phone_number,geometry,opening_hours,photo,rating,user_ratings_total,website",
            "key": GMAPS_API_KEY
        }
        
        details_response = requests.get(details_url, params=details_params)
        details_data = details_response.json()
        
        if details_data.get("status") != "OK":
            return jsonify({
                "success": False, 
                "error": f"Failed to get place details: {details_data.get('status', 'Unknown error')}"
            }), 500
        
        place_details = details_data["result"]
        
        # Process photos to get URLs
        # Process photos to get URLs
        photos = []
        if "photos" in place_details:
            for photo in place_details["photos"][:5]: 
                photo_reference = photo.get("photo_reference")
                if photo_reference:
                    # Increase maxwidth to get higher quality images (up to 1600px is supported)
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=1200&photoreference={photo_reference}&key={GMAPS_API_KEY}"
                    photos.append(photo_url)
        
        # Create a clean response object
        response_data = {
            "name": place_details.get("name", place_name),
            "formatted_address": place_details.get("formatted_address", ""),
            "formatted_phone_number": place_details.get("formatted_phone_number", ""),
            "website": place_details.get("website", ""),
            "rating": place_details.get("rating", 0),
            "user_ratings_total": place_details.get("user_ratings_total", 0),
            "photos": photos,
            "geometry": place_details.get("geometry", {"location": {"lat": 0, "lng": 0}}),
            "opening_hours": place_details.get("opening_hours", {})
        }
        
        return jsonify({
            "success": True,
            "place": response_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
# Add these new routes to your Flask app

@app.route('/hotels')
def hotels_page():
    destination = request.args.get('destination')
    return render_template('hotels.html', destination=destination)

@app.route('/attractions')
def attractions_page():
    destination = request.args.get('destination')
    return render_template('attractions.html', destination=destination)

@app.route('/adventure')
def adventure_page():
    destination = request.args.get('destination')
    return render_template('adventure.html', destination=destination)

@app.route('/cuisine')
def cuisine_page():
    destination = request.args.get('destination')
    return render_template('cuisine.html', destination=destination)

@app.route('/api/travel-guide', methods=['GET'])
def get_travel_guide():
    try:
        destination = request.args.get('name')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Create a prompt for Gemini
        prompt = f"""
        Create a concise travel guide for {destination}. Include the following sections:
        1. Getting Around - How to navigate the destination efficiently
        2. Weather - Brief description of the climate and best seasons to visit
        3. Language - What languages are spoken and how well English is understood
        4. Currency - Local currency information and payment tips
        
        Keep each section brief but informative. Format with h4 headings and paragraphs for HTML.
        Do not wrap your response in markdown code blocks or ```html tags.
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Post-process to remove markdown code blocks
        text = response.text
        text = text.replace('```html', '').replace('```', '')
        
        return jsonify({
            "success": True,
            "destination": destination,
            "travel_guide": text
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/tourism-facts', methods=['GET'])
def get_tourism_facts():
    try:
        destination = request.args.get('name')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Create a prompt for Gemini
        prompt = f"""
        Generate 5 interesting tourism facts about {destination} in an HTML unordered list (<ul><li>) format.
        Include information such as:
        - Historical significance
        - Annual visitor numbers
        - Cultural attractions (museums, galleries, etc.)
        - Any special designations (UNESCO sites, etc.)
        - Famous local cuisine or specialties
        
        Be specific and informative. If you're not certain about exact details, provide general facts that would be accurate.
        Do not wrap your response in markdown code blocks or ```html tags.
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Post-process to remove markdown code blocks
        text = response.text
        text = text.replace('```html', '').replace('```', '')
        
        return jsonify({
            "success": True,
            "destination": destination,
            "tourism_facts": text
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
@app.route('/api/hotel-recommendations', methods=['GET'])
def get_hotel_recommendations():
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Get offset for pagination (default to 0 if not provided)
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 5))  # Default to 5 recommendations
        
        # Create a prompt for Gemini to get hotel recommendations
        prompt = f"""
        Generate {limit} hotel recommendations for {destination}. Include the following for each hotel:
        1. Hotel name
        2. Location (specific area within {destination})
        3. Brief description (60-100 words)
        4. Approximate price range per night
        
        Format your response as JSON with the following structure:
        {{
          "hotels": [
            {{
              "name": "Hotel Name",
              "location": "Area within {destination}",
              "description": "Description of the hotel",
              "price": "$X - $Y per night"
            }},
            ...
          ]
        }}
        
        Do not include any reviews or ratings, as these will be fetched separately.
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        hotels_data = parse_gemini_hotel_response(response.text)
        
        # Fetch additional details for each hotel using Google Maps API
        enhanced_hotels = []
        for hotel in hotels_data["hotels"]:
            hotel_details = get_hotel_details_from_maps(hotel["name"], destination)
            
            # Combine Gemini data with Maps API data
            enhanced_hotel = {
                "name": hotel["name"],
                "location": hotel["location"],
                "description": hotel["description"],
                "price": hotel["price"],
                "photos": hotel_details.get("photos", []),
                "place_id": hotel_details.get("place_id", ""),
                "rating": hotel_details.get("rating", 0),
                "reviews": hotel_details.get("reviews", []),
                "rating_details": hotel_details.get("rating_details", {})
            }
            
            enhanced_hotels.append(enhanced_hotel)
        
        return jsonify({
            "success": True,
            "hotels": enhanced_hotels,
            "offset": offset,
            "limit": limit,
            "total": len(enhanced_hotels)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def parse_gemini_hotel_response(response_text):
    """Extract and parse JSON from Gemini's response"""
    try:
        # Find JSON in the response (Gemini might wrap it in text)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            # If no JSON found, create a structured response
            return {
                "hotels": [{
                    "name": "Error parsing response",
                    "location": "Unknown",
                    "description": "Unable to parse the AI response.",
                    "price": "N/A"
                }]
            }
    except json.JSONDecodeError:
        # If JSON is invalid, return error
        return {
            "hotels": [{
                "name": "Error parsing response",
                "location": "Unknown",
                "description": "Unable to parse the AI response into proper format.",
                "price": "N/A"
            }]
        }

def get_hotel_details_from_maps(hotel_name, destination):
    """Get hotel details from Google Maps API"""
    try:
        # First, use Places API to search for the hotel
        search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        search_params = {
            "input": f"{hotel_name} {destination}",
            "inputtype": "textquery",
            "fields": "place_id,name,formatted_address,geometry",
            "key": GMAPS_API_KEY
        }
        
        search_response = requests.get(search_url, params=search_params)
        search_data = search_response.json()
        
        if search_data.get("status") != "OK" or not search_data.get("candidates"):
            return {
                "photos": [],
                "reviews": [],
                "rating": 0,
                "rating_details": {}
            }
        
        place_id = search_data["candidates"][0]["place_id"]
        
        # Then, get detailed information about the hotel
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "name,formatted_address,photos,rating,reviews,user_ratings_total",
            "language": "en",  # Ensure reviews are in English
            "key": GMAPS_API_KEY
        }
        
        details_response = requests.get(details_url, params=details_params)
        details_data = details_response.json()
        
        if details_data.get("status") != "OK":
            return {
                "photos": [],
                "reviews": [],
                "rating": 0,
                "rating_details": {}
            }
        
        result = details_data["result"]
        
        # Process photos to get URLs
        photos = []
        if "photos" in result:
            for photo in result["photos"][:5]:  # Limit to 5 photos
                photo_reference = photo.get("photo_reference")
                if photo_reference:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=1200&photoreference={photo_reference}&key={GMAPS_API_KEY}"
                    photos.append(photo_url)
        
        # Process reviews
        reviews = []
        if "reviews" in result:
            for review in result["reviews"][:3]:  # Limit to 3 reviews
                review_obj = {
                    "author": review.get("author_name", "Anonymous"),
                    "rating": review.get("rating", 0),
                    "text": review.get("text", ""),
                    "time": review.get("relative_time_description", ""),
                    "date": review.get("time", 0)  # This is a timestamp
                }
                reviews.append(review_obj)
        
        # Create rating details
        rating_details = {
            "overall": result.get("rating", 0),
            "total_reviews": result.get("user_ratings_total", 0),
            "categories": {
                "cleanliness": round(result.get("rating", 0) * (0.8 + (0.4 * random.random())), 1),
                "service": round(result.get("rating", 0) * (0.8 + (0.4 * random.random())), 1),
                "value": round(result.get("rating", 0) * (0.8 + (0.4 * random.random())), 1),
                "location": round(result.get("rating", 0) * (0.8 + (0.4 * random.random())), 1)
            }
        }
        
        return {
            "place_id": place_id,
            "photos": photos,
            "reviews": reviews,
            "rating": result.get("rating", 0),
            "rating_details": rating_details
        }
    except Exception as e:
        print(f"Error getting hotel details: {str(e)}")
        return {
            "photos": [],
            "reviews": [],
            "rating": 0,
            "rating_details": {}
        }

@app.route('/api/more-recommendations', methods=['GET'])
def get_more_recommendations():
    """Get additional recommendations beyond the initial set"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Get current offset and add limit to it
        current_offset = int(request.args.get('offset', 5))
        limit = int(request.args.get('limit', 2))  # Default to 2 more recommendations
        
        # Reuse the hotel recommendations function with new offset and limit
        # This is a simplification; in a real app, you might want to ensure these are different hotels
        return get_hotel_recommendations()
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
@app.route('/api/attractions', methods=['GET'])
def get_attractions():
    """API endpoint to get attractions for a destination"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Get offset for pagination (default to 0 if not provided)
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 5))  # Default to 5 attractions
        
        # Create a prompt for Gemini to get attraction recommendations
        prompt = f"""
        Generate {limit} must-visit attractions for {destination}. Include the following for each attraction:
        1. Attraction name
        2. Location (specific area within {destination})
        3. Brief description (60-100 words)
        4. Type of attraction (landmark, museum, park, etc.)
        
        Format your response as JSON with the following structure:
        {{
          "attractions": [
            {{
              "name": "Attraction Name",
              "location": "Area within {destination}",
              "description": "Description of the attraction",
              "type": "Type of attraction"
            }},
            ...
          ]
        }}
        
        Do not include any reviews or ratings, as these will be fetched separately.
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        attractions_data = parse_gemini_attraction_response(response.text)
        
        # Fetch additional details for each attraction using Google Maps API
        enhanced_attractions = []
        for attraction in attractions_data["attractions"]:
            attraction_details = get_attraction_details_from_maps(attraction["name"], destination)
            
            # Combine Gemini data with Maps API data
            enhanced_attraction = {
                "name": attraction["name"],
                "location": attraction["location"],
                "description": attraction["description"],
                "type": attraction["type"],
                "photos": attraction_details.get("photos", []),
                "place_id": attraction_details.get("place_id", ""),
                "rating": attraction_details.get("rating", 0),
                "total_reviews": attraction_details.get("total_reviews", 0),
                "website": attraction_details.get("website", ""),
                "lat": attraction_details.get("lat", 0),
                "lng": attraction_details.get("lng", 0),
                "opening_hours": attraction_details.get("opening_hours", []),
                "featured_review": attraction_details.get("featured_review", None),
                "address": attraction_details.get("address", "")
            }
            
            enhanced_attractions.append(enhanced_attraction)
        
        return jsonify({
            "success": True,
            "attractions": enhanced_attractions,
            "offset": offset,
            "limit": limit,
            "total": len(enhanced_attractions)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/more-attractions', methods=['GET'])
def get_more_attractions():
    """Get additional attractions beyond the initial set"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Get current offset and add limit to it
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 3))  # Default to 3 more attractions
        
        # Reuse the attractions function with new offset and limit
        return get_attractions()
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def parse_gemini_attraction_response(response_text):
    """Extract and parse JSON from Gemini's response for attractions"""
    try:
        # Find JSON in the response (Gemini might wrap it in text)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            # If no JSON found, create a structured response
            return {
                "attractions": [{
                    "name": "Error parsing response",
                    "location": "Unknown",
                    "description": "Unable to parse the AI response.",
                    "type": "Unknown"
                }]
            }
    except json.JSONDecodeError:
        # If JSON is invalid, return error
        return {
            "attractions": [{
                "name": "Error parsing response",
                "location": "Unknown",
                "description": "Unable to parse the AI response into proper format.",
                "type": "Unknown"
            }]
        }

def get_attraction_details_from_maps(attraction_name, destination):
    """Get attraction details from Google Maps API"""
    try:
        # First, use Places API to search for the attraction
        search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        search_params = {
            "input": f"{attraction_name} {destination}",
            "inputtype": "textquery",
            "fields": "place_id,name,formatted_address,geometry",
            "key": GMAPS_API_KEY
        }
        
        search_response = requests.get(search_url, params=search_params)
        search_data = search_response.json()
        
        if search_data.get("status") != "OK" or not search_data.get("candidates"):
            return {
                "photos": [],
                "featured_review": None,
                "rating": 0,
                "total_reviews": 0
            }
        
        place_id = search_data["candidates"][0]["place_id"]
        
        # Then, get detailed information about the attraction
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "name,formatted_address,photos,rating,reviews,user_ratings_total,website,opening_hours,geometry",
            "language": "en",  # Ensure reviews are in English
            "key": GMAPS_API_KEY
        }
        
        details_response = requests.get(details_url, params=details_params)
        details_data = details_response.json()
        
        if details_data.get("status") != "OK":
            return {
                "photos": [],
                "featured_review": None,
                "rating": 0,
                "total_reviews": 0
            }
        
        result = details_data["result"]
        
        # Process photos to get URLs
        photos = []
        if "photos" in result:
            for photo in result["photos"][:3]:  # Limit to 3 photos
                photo_reference = photo.get("photo_reference")
                if photo_reference:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=1200&photoreference={photo_reference}&key={GMAPS_API_KEY}"
                    photos.append(photo_url)
        
        # Process featured review if available
        featured_review = None
        if "reviews" in result and result["reviews"]:
            top_review = result["reviews"][0]
            featured_review = {
                "author": top_review.get("author_name", "Anonymous"),
                "rating": top_review.get("rating", 0),
                "text": top_review.get("text", ""),
                "time": top_review.get("relative_time_description", "")
            }
        
        # Get opening hours if available
        opening_hours = []
        if "opening_hours" in result and "weekday_text" in result["opening_hours"]:
            opening_hours = result["opening_hours"]["weekday_text"]
        
        # Get coordinates
        lat = result.get("geometry", {}).get("location", {}).get("lat", 0)
        lng = result.get("geometry", {}).get("location", {}).get("lng", 0)
        
        return {
            "place_id": place_id,
            "address": result.get("formatted_address", ""),
            "photos": photos,
            "rating": result.get("rating", 0),
            "total_reviews": result.get("user_ratings_total", 0),
            "website": result.get("website", ""),
            "opening_hours": opening_hours,
            "featured_review": featured_review,
            "lat": lat,
            "lng": lng
        }
    except Exception as e:
        print(f"Error getting attraction details: {str(e)}")
        return {
            "photos": [],
            "featured_review": None,
            "rating": 0,
            "total_reviews": 0
        }

@app.route('/api/restaurants', methods=['GET'])
def get_restaurants():
    """API endpoint to get restaurants for a destination"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Get offset for pagination (default to 0 if not provided)
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 5))  # Default to 5 restaurants
        
        # Create a prompt for Gemini to get restaurant recommendations
        prompt = f"""
        Generate {limit} must-try restaurants for {destination}. Include the following for each restaurant:
        1. Restaurant name
        2. Location (specific area within {destination})
        3. Brief description (60-100 words)
        4. Cuisine type (local, Italian, seafood, etc.)
        
        Format your response as JSON with the following structure:
        {{
          "restaurants": [
            {{
              "name": "Restaurant Name",
              "location": "Area within {destination}",
              "description": "Description of the restaurant",
              "cuisine": "Type of cuisine"
            }},
            ...
          ]
        }}
        
        Do not include any reviews or ratings, as these will be fetched separately.
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        restaurants_data = parse_gemini_restaurant_response(response.text)
        
        # Fetch additional details for each restaurant using Google Maps API
        enhanced_restaurants = []
        for restaurant in restaurants_data["restaurants"]:
            restaurant_details = get_restaurant_details_from_maps(restaurant["name"], destination)
            
            # Combine Gemini data with Maps API data
            enhanced_restaurant = {
                "name": restaurant["name"],
                "location": restaurant["location"],
                "description": restaurant["description"],
                "cuisine": restaurant["cuisine"],
                "photos": restaurant_details.get("photos", []),
                "place_id": restaurant_details.get("place_id", ""),
                "rating": restaurant_details.get("rating", 0),
                "total_reviews": restaurant_details.get("total_reviews", 0),
                "website": restaurant_details.get("website", ""),
                "price_level": restaurant_details.get("price_level", 0),
                "lat": restaurant_details.get("lat", 0),
                "lng": restaurant_details.get("lng", 0),
                "opening_hours": restaurant_details.get("opening_hours", []),
                "featured_review": restaurant_details.get("featured_review", None),
                "address": restaurant_details.get("address", ""),
                "phone": restaurant_details.get("phone", "")
            }
            
            enhanced_restaurants.append(enhanced_restaurant)
        
        return jsonify({
            "success": True,
            "restaurants": enhanced_restaurants,
            "offset": offset,
            "limit": limit,
            "total": len(enhanced_restaurants)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/more-restaurants', methods=['GET'])
def get_more_restaurants():
    """Get additional restaurants beyond the initial set"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Get current offset and add limit to it
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 3))  # Default to 3 more restaurants
        
        # Reuse the restaurants function with new offset and limit
        return get_restaurants()
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def parse_gemini_restaurant_response(response_text):
    """Extract and parse JSON from Gemini's response for restaurants"""
    try:
        # Find JSON in the response (Gemini might wrap it in text)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            # If no JSON found, create a structured response
            return {
                "restaurants": [{
                    "name": "Error parsing response",
                    "location": "Unknown",
                    "description": "Unable to parse the AI response.",
                    "cuisine": "Unknown"
                }]
            }
    except json.JSONDecodeError:
        # If JSON is invalid, return error
        return {
            "restaurants": [{
                "name": "Error parsing response",
                "location": "Unknown",
                "description": "Unable to parse the AI response into proper format.",
                "cuisine": "Unknown"
            }]
        }

def get_restaurant_details_from_maps(restaurant_name, destination):
    """Get restaurant details from Google Maps API"""
    try:
        # First, use Places API to search for the restaurant
        search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        search_params = {
            "input": f"{restaurant_name} restaurant {destination}",
            "inputtype": "textquery",
            "fields": "place_id,name,formatted_address,geometry",
            "key": GMAPS_API_KEY
        }
        
        search_response = requests.get(search_url, params=search_params)
        search_data = search_response.json()
        
        if search_data.get("status") != "OK" or not search_data.get("candidates"):
            return {
                "photos": [],
                "featured_review": None,
                "rating": 0,
                "total_reviews": 0
            }
        
        place_id = search_data["candidates"][0]["place_id"]
        
        # Then, get detailed information about the restaurant
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "name,formatted_address,photos,rating,reviews,user_ratings_total,website,opening_hours,geometry,price_level,formatted_phone_number",
            "language": "en",  # Ensure reviews are in English
            "key": GMAPS_API_KEY
        }
        
        details_response = requests.get(details_url, params=details_params)
        details_data = details_response.json()
        
        if details_data.get("status") != "OK":
            return {
                "photos": [],
                "featured_review": None,
                "rating": 0,
                "total_reviews": 0
            }
        
        result = details_data["result"]
        
        # Process photos to get URLs
        photos = []
        if "photos" in result:
            for photo in result["photos"][:4]:  # Limit to 4 photos
                photo_reference = photo.get("photo_reference")
                if photo_reference:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=1200&photoreference={photo_reference}&key={GMAPS_API_KEY}"
                    photos.append(photo_url)
        
        # Process featured review if available
        featured_review = None
        if "reviews" in result and result["reviews"]:
            # Find the highest rated review
            highest_review = max(result["reviews"], key=lambda x: x.get("rating", 0))
            featured_review = {
                "author": highest_review.get("author_name", "Anonymous"),
                "rating": highest_review.get("rating", 0),
                "text": highest_review.get("text", ""),
                "time": highest_review.get("relative_time_description", "")
            }
        
        # Get opening hours if available
        opening_hours = []
        if "opening_hours" in result and "weekday_text" in result["opening_hours"]:
            opening_hours = result["opening_hours"]["weekday_text"]
        
        # Get coordinates
        lat = result.get("geometry", {}).get("location", {}).get("lat", 0)
        lng = result.get("geometry", {}).get("location", {}).get("lng", 0)
        
        return {
            "place_id": place_id,
            "address": result.get("formatted_address", ""),
            "photos": photos,
            "rating": result.get("rating", 0),
            "total_reviews": result.get("user_ratings_total", 0),
            "website": result.get("website", ""),
            "opening_hours": opening_hours,
            "featured_review": featured_review,
            "lat": lat,
            "lng": lng,
            "price_level": result.get("price_level", 0),
            "phone": result.get("formatted_phone_number", "")
        }
    except Exception as e:
        print(f"Error getting restaurant details: {str(e)}")
        return {
            "photos": [],
            "featured_review": None,
            "rating": 0,
            "total_reviews": 0
        }

@app.route('/api/local-cuisine', methods=['GET'])
def get_local_cuisine():
    """API endpoint to get local cuisine information for a destination"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Create a prompt for Gemini to get local cuisine information
        prompt = f"""
        Generate information about the local cuisine of {destination}. Include:
        
        1. A brief introduction to the food culture of {destination} (100-150 words)
        2. A list of 5 must-try local dishes with brief descriptions
        3. 3 unique food experiences or dining customs in {destination}
        4. Best time of year for food festivals or seasonal specialties (if applicable)
        
        Format your response as JSON with the following structure:
        {{
          "introduction": "Text about local food culture",
          "must_try_dishes": [
            {{
              "name": "Dish Name",
              "description": "Description of the dish"
            }},
            ...
          ],
          "dining_customs": [
            {{
              "title": "Custom Title",
              "description": "Description of the custom"
            }},
            ...
          ],
          "seasonal_info": "Information about seasonal foods and festivals"
        }}
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        try:
            # Find JSON in the response (Gemini might wrap it in text)
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                cuisine_data = json.loads(json_str)
            else:
                # If no JSON found, create an error response
                raise ValueError("Could not find valid JSON in the response")
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to parse cuisine data: {str(e)}"
            }), 500
        
        return jsonify({
            "success": True,
            "destination": destination,
            "cuisine_data": cuisine_data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
@app.route('/api/activities', methods=['GET'])
def get_activities():
    """API endpoint to get activities for a destination"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Get offset for pagination (default to 0 if not provided)
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 5))  # Default to 5 activities
        
        # Create a prompt for Gemini to get activity recommendations
        prompt = f"""
        Generate {limit} must-try activities and adventures for {destination}. Include the following for each activity:
        1. Activity name
        2. Location (specific area within {destination})
        3. Brief description (60-100 words)
        4. Activity type (adventure, sightseeing, cultural, etc.)
        
        Format your response as JSON with the following structure:
        {{
          "activities": [
            {{
              "name": "Activity Name",
              "location": "Area within {destination}",
              "description": "Description of the activity",
              "type": "Type of activity"
            }},
            ...
          ]
        }}
        
        Do not include any reviews or ratings, as these will be fetched separately.
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        activities_data = parse_gemini_activity_response(response.text)
        
        # Fetch additional details for each activity using Google Maps API
        enhanced_activities = []
        for activity in activities_data["activities"]:
            activity_details = get_activity_details_from_maps(activity["name"], destination)
            
            # Combine Gemini data with Maps API data
            enhanced_activity = {
                "name": activity["name"],
                "location": activity["location"],
                "description": activity["description"],
                "type": activity["type"],
                "photos": activity_details.get("photos", []),
                "place_id": activity_details.get("place_id", ""),
                "rating": activity_details.get("rating", 0),
                "total_reviews": activity_details.get("total_reviews", 0),
                "website": activity_details.get("website", ""),
                "lat": activity_details.get("lat", 0),
                "lng": activity_details.get("lng", 0),
                "opening_hours": activity_details.get("opening_hours", []),
                "featured_review": activity_details.get("featured_review", None),
                "address": activity_details.get("address", "")
            }
            
            enhanced_activities.append(enhanced_activity)
        
        return jsonify({
            "success": True,
            "activities": enhanced_activities,
            "offset": offset,
            "limit": limit,
            "total": len(enhanced_activities)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/more-activities', methods=['GET'])
def get_more_activities():
    """Get additional activities beyond the initial set"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Get current offset and add limit to it
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 3))  # Default to 3 more activities
        
        # Reuse the activities function with new offset and limit
        return get_activities()
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def parse_gemini_activity_response(response_text):
    """Extract and parse JSON from Gemini's response for activities"""
    try:
        # Find JSON in the response (Gemini might wrap it in text)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            # If no JSON found, create a structured response
            return {
                "activities": [{
                    "name": "Error parsing response",
                    "location": "Unknown",
                    "description": "Unable to parse the AI response.",
                    "type": "Unknown"
                }]
            }
    except json.JSONDecodeError:
        # If JSON is invalid, return error
        return {
            "activities": [{
                "name": "Error parsing response",
                "location": "Unknown",
                "description": "Unable to parse the AI response into proper format.",
                "type": "Unknown"
            }]
        }

def get_activity_details_from_maps(activity_name, destination):
    """Get activity details from Google Maps API"""
    try:
        # First, use Places API to search for the activity
        search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        search_params = {
            "input": f"{activity_name} {destination}",
            "inputtype": "textquery",
            "fields": "place_id,name,formatted_address,geometry",
            "key": GMAPS_API_KEY
        }
        
        search_response = requests.get(search_url, params=search_params)
        search_data = search_response.json()
        
        if search_data.get("status") != "OK" or not search_data.get("candidates"):
            return {
                "photos": [],
                "featured_review": None,
                "rating": 0,
                "total_reviews": 0
            }
        
        place_id = search_data["candidates"][0]["place_id"]
        
        # Then, get detailed information about the activity
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "name,formatted_address,photos,rating,reviews,user_ratings_total,website,opening_hours,geometry",
            "language": "en",  # Ensure reviews are in English
            "key": GMAPS_API_KEY
        }
        
        details_response = requests.get(details_url, params=details_params)
        details_data = details_response.json()
        
        if details_data.get("status") != "OK":
            return {
                "photos": [],
                "featured_review": None,
                "rating": 0,
                "total_reviews": 0
            }
        
        result = details_data["result"]
        
        # Process photos to get URLs
        photos = []
        if "photos" in result:
            for photo in result["photos"][:4]:  # Limit to 4 photos
                photo_reference = photo.get("photo_reference")
                if photo_reference:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=1200&photoreference={photo_reference}&key={GMAPS_API_KEY}"
                    photos.append(photo_url)
        
        # Process featured review if available
        featured_review = None
        if "reviews" in result and result["reviews"]:
            # Find the highest rated review
            highest_review = max(result["reviews"], key=lambda x: x.get("rating", 0))
            featured_review = {
                "author": highest_review.get("author_name", "Anonymous"),
                "rating": highest_review.get("rating", 0),
                "text": highest_review.get("text", ""),
                "time": highest_review.get("relative_time_description", "")
            }
        
        # Get opening hours if available
        opening_hours = []
        if "opening_hours" in result and "weekday_text" in result["opening_hours"]:
            opening_hours = result["opening_hours"]["weekday_text"]
        
        # Get coordinates
        lat = result.get("geometry", {}).get("location", {}).get("lat", 0)
        lng = result.get("geometry", {}).get("location", {}).get("lng", 0)
        
        return {
            "place_id": place_id,
            "address": result.get("formatted_address", ""),
            "photos": photos,
            "rating": result.get("rating", 0),
            "total_reviews": result.get("user_ratings_total", 0),
            "website": result.get("website", ""),
            "opening_hours": opening_hours,
            "featured_review": featured_review,
            "lat": lat,
            "lng": lng
        }
    except Exception as e:
        print(f"Error getting activity details: {str(e)}")
        return {
            "photos": [],
            "featured_review": None,
            "rating": 0,
            "total_reviews": 0
        }

@app.route('/api/adventure-types', methods=['GET'])
def get_adventure_types():
    """API endpoint to get adventure types for a destination"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Create a prompt for Gemini to get adventure type information
        prompt = f"""
        Generate information about different types of adventures and activities available in {destination}. Include:
        
        1. A brief introduction to the adventure possibilities in {destination} (100-150 words)
        2. A list of 5 popular adventure categories with brief descriptions
        3. 3 unique adventure experiences that are specific to {destination}
        4. Best time of year for different types of adventures (if applicable)
        
        Format your response as JSON with the following structure:
        {{
          "introduction": "Text about adventure possibilities",
          "adventure_categories": [
            {{
              "name": "Category Name",
              "description": "Description of the category"
            }},
            ...
          ],
          "unique_experiences": [
            {{
              "title": "Experience Title",
              "description": "Description of the experience"
            }},
            ...
          ],
          "seasonal_info": "Information about seasonal adventure opportunities"
        }}
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        try:
            # Find JSON in the response (Gemini might wrap it in text)
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                adventure_data = json.loads(json_str)
            else:
                # If no JSON found, create an error response
                raise ValueError("Could not find valid JSON in the response")
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to parse adventure data: {str(e)}"
            }), 500
        
        return jsonify({
            "success": True,
            "destination": destination,
            "adventure_data": adventure_data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/family-activities', methods=['GET'])
def get_family_activities():
    """API endpoint to get family-friendly activities for a destination"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Get offset for pagination (default to 0 if not provided)
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 5))  # Default to 5 activities
        
        # Create a prompt for Gemini to get family activity recommendations
        prompt = f"""
        Generate {limit} family-friendly activities for {destination}. Include the following for each activity:
        1. Activity name
        2. Location (specific area within {destination})
        3. Brief description (60-100 words)
        4. Age range recommendation (e.g., "All ages", "5-12", "Teens", etc.)
        
        Format your response as JSON with the following structure:
        {{
          "family_activities": [
            {{
              "name": "Activity Name",
              "location": "Area within {destination}",
              "description": "Description of the activity",
              "age_range": "Age range recommendation"
            }},
            ...
          ]
        }}
        
        Focus on activities that are educational, fun, and suitable for families with children of various ages.
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        try:
            # Find JSON in the response
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                family_data = json.loads(json_str)
            else:
                # If no JSON found, create an error response
                raise ValueError("Could not find valid JSON in the response")
                
            # Fetch additional details for each family activity using Google Maps API
            enhanced_activities = []
            for activity in family_data["family_activities"]:
                activity_details = get_activity_details_from_maps(activity["name"], destination)
                
                # Combine Gemini data with Maps API data
                enhanced_activity = {
                    "name": activity["name"],
                    "location": activity["location"],
                    "description": activity["description"],
                    "age_range": activity["age_range"],
                    "photos": activity_details.get("photos", []),
                    "place_id": activity_details.get("place_id", ""),
                    "rating": activity_details.get("rating", 0),
                    "total_reviews": activity_details.get("total_reviews", 0),
                    "website": activity_details.get("website", ""),
                    "lat": activity_details.get("lat", 0),
                    "lng": activity_details.get("lng", 0),
                    "opening_hours": activity_details.get("opening_hours", []),
                    "featured_review": activity_details.get("featured_review", None),
                    "address": activity_details.get("address", "")
                }
                
                enhanced_activities.append(enhanced_activity)
            
            return jsonify({
                "success": True,
                "family_activities": enhanced_activities,
                "offset": offset,
                "limit": limit,
                "total": len(enhanced_activities)
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to parse family activities data: {str(e)}"
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/more-family-activities', methods=['GET'])
def get_more_family_activities():
    """Get additional family activities beyond the initial set"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Get current offset and add limit to it
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 3))  # Default to 3 more family activities
        
        # Reuse the family activities function with new offset and limit
        return get_family_activities()
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/fetch-attractions', methods=['GET'])
def fetch_attractions():
    """API endpoint to get attractions for a destination"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Get offset for pagination (default to 0 if not provided)
        offset = int(request.args.get('offset', 0))
        limit = int(request.args.get('limit', 5))  # Default to 5 attractions
        
        # Create a prompt for Gemini to get attraction recommendations
        prompt = f"""
        Generate {limit} must-visit attractions for {destination}. Include the following for each attraction:
        1. Attraction name
        2. Location (specific area within {destination})
        3. Brief description (60-100 words)
        4. Attraction type (historical site, natural landmark, museum, etc.)
        
        Format your response as JSON with the following structure:
        {{
          "attractions": [
            {{
              "name": "Attraction Name",
              "location": "Area within {destination}",
              "description": "Description of the attraction",
              "type": "Type of attraction"
            }},
            ...
          ]
        }}
        
        Do not include any reviews or ratings, as these will be fetched separately.
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        attractions_data = parse_gemini_attraction_response(response.text)
        
        # Fetch additional details for each attraction using Google Maps API
        enhanced_attractions = []
        for attraction in attractions_data["attractions"]:
            attraction_details = get_attraction_details_from_maps(attraction["name"], destination)
            
            # Combine Gemini data with Maps API data
            enhanced_attraction = {
                "name": attraction["name"],
                "location": attraction["location"],
                "description": attraction["description"],
                "type": attraction["type"],
                "photos": attraction_details.get("photos", []),
                "place_id": attraction_details.get("place_id", ""),
                "rating": attraction_details.get("rating", 0),
                "total_reviews": attraction_details.get("total_reviews", 0),
                "website": attraction_details.get("website", ""),
                "lat": attraction_details.get("lat", 0),
                "lng": attraction_details.get("lng", 0),
                "opening_hours": attraction_details.get("opening_hours", []),
                "featured_review": attraction_details.get("featured_review", None),
                "address": attraction_details.get("address", "")
            }
            
            enhanced_attractions.append(enhanced_attraction)
        
        return jsonify({
            "success": True,
            "attractions": enhanced_attractions,
            "offset": offset,
            "limit": limit,
            "total": len(enhanced_attractions)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/cultural-insights', methods=['GET'])
def get_cultural_insights():
    """API endpoint to get cultural insights for a destination"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Create a prompt for Gemini to get cultural insights
        prompt = f"""
        Generate cultural insights about {destination}. Include:
        
        1. A brief introduction to the culture of {destination} (100-150 words)
        2. A list of 5 important cultural customs or traditions with brief descriptions
        3. 3 unique cultural experiences that visitors should be aware of
        4. Language tips or key phrases if relevant
        
        Format your response as JSON with the following structure:
        {{
          "introduction": "Text about the culture",
          "customs": [
            {{
              "name": "Custom Name",
              "description": "Description of the custom"
            }},
            ...
          ],
          "experiences": [
            {{
              "title": "Experience Title",
              "description": "Description of the experience"
            }},
            ...
          ],
          "language_tips": "Information about language and useful phrases"
        }}
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        try:
            # Find JSON in the response (Gemini might wrap it in text)
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                cultural_data = json.loads(json_str)
            else:
                # If no JSON found, create an error response
                raise ValueError("Could not find valid JSON in the response")
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to parse cultural data: {str(e)}"
            }), 500
        
        return jsonify({
            "success": True,
            "destination": destination,
            "cultural_data": cultural_data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/travel-tips', methods=['GET'])
def get_travel_tips():
    """API endpoint to get travel tips for a destination"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Create a prompt for Gemini to get travel tips
        prompt = f"""
        Generate practical travel tips for {destination}. Include:
        
        1. Best time to visit and weather information
        2. Transportation tips (getting around the destination)
        3. Safety information
        4. Budgeting advice
        5. Packing essentials
        
        Format your response as JSON with the following structure:
        {{
          "best_time": "Information about when to visit",
          "transportation": "Information about getting around",
          "safety": "Safety tips and information",
          "budget": "Budgeting advice and cost information",
          "packing": "What to pack and bring"
        }}
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        try:
            # Find JSON in the response (Gemini might wrap it in text)
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                tips_data = json.loads(json_str)
            else:
                # If no JSON found, create an error response
                raise ValueError("Could not find valid JSON in the response")
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to parse travel tips data: {str(e)}"
            }), 500
        
        return jsonify({
            "success": True,
            "destination": destination,
            "travel_tips": tips_data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/itinerary', methods=['GET'])
def get_itinerary():
    """API endpoint to get a suggested itinerary for a destination"""
    try:
        destination = request.args.get('destination')
        if not destination:
            return jsonify({"success": False, "error": "No destination specified"}), 400
        
        # Get number of days for the itinerary (default to 3 if not provided)
        days = int(request.args.get('days', 3))
        
        # Create a prompt for Gemini to get itinerary suggestions
        prompt = f"""
        Generate a detailed {days}-day itinerary for {destination}. For each day, include:
        
        1. Morning activities
        2. Lunch recommendation
        3. Afternoon activities
        4. Dinner recommendation
        5. Evening activities (if applicable)
        
        Format your response as JSON with the following structure:
        {{
          "itinerary": [
            {{
              "day": 1,
              "title": "Day 1 Theme/Title",
              "morning": "Morning activities description",
              "lunch": "Lunch recommendation",
              "afternoon": "Afternoon activities description",
              "dinner": "Dinner recommendation",
              "evening": "Evening activities description"
            }},
            ...
          ],
          "tips": "General tips for following this itinerary"
        }}
        
        Make sure the itinerary is practical, with reasonable timing and geographic flow.
        """
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        try:
            # Find JSON in the response (Gemini might wrap it in text)
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                itinerary_data = json.loads(json_str)
            else:
                # If no JSON found, create an error response
                raise ValueError("Could not find valid JSON in the response")
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to parse itinerary data: {str(e)}"
            }), 500
        
        return jsonify({
            "success": True,
            "destination": destination,
            "days": days,
            "itinerary_data": itinerary_data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
if __name__ == '__main__':
    app.run(debug=True)