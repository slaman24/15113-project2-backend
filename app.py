import os
import json
import datetime
import random
import requests
from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# --- SECRETS LOADER ---
def load_secrets():
    """Reads secrets.txt and loads them into environment variables."""
    try:
        with open("secrets.txt", "r") as file:
            for line in file:
                # Clean up any accidental whitespace or hidden newline characters
                line = line.strip()
                
                # Ignore empty lines or comments
                if line and not line.startswith("#"):
                    # Split only on the first '=' in case the key itself contains an '='
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        # This will silently pass when deployed on Render, which is exactly what we want!
        print("Warning: secrets.txt not found. Using system environment variables.")

# Call the function immediately so the keys are ready to use
load_secrets()

app = Flask(__name__)
# Enable CORS so your frontend can communicate with this backend
CORS(app)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local_puzzles.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODEL ---
class DailyPuzzle(db.Model):
    __tablename__ = 'daily_puzzles'
    puzzle_date = db.Column(db.Date, primary_key=True)
    puzzle_data = db.Column(db.JSON, nullable=False)

# --- API PIPELINE FUNCTIONS ---
def generate_categories_with_openai():
    """Calls the OpenAI API to generate the 4 categories and 16 search queries."""
    print("1. Calling OpenAI to generate puzzle categories...")
    url = "https://api.openai.com/v1/chat/completions"
    api_key = os.environ.get("OPENAI_API_KEY")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # The strict system prompt guarantees we get the exact JSON structure we need
    system_prompt = """
    You are a clever puzzle designer for a daily YouTube-themed connections game. 
    Generate 4 distinct, engaging categories related to YouTube video genres. 
    For each category, provide exactly 4 highly specific YouTube search queries that will reliably return a relevant video.
    
    Format your response strictly as JSON matching this structure:
    {
      "categories": [
        {
          "category_name": "Example Category",
          "search_queries": ["query 1", "query 2", "query 3", "query 4"]
        }
      ]
    }
    """
    
    payload = {
        "model": "gpt-4o-mini",
        "response_format": { "type": "json_object" },
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate today's YouTube connections puzzle."}
        ],
        "temperature": 0.7
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        content_string = response.json()["choices"][0]["message"]["content"]
        # Convert the JSON string returned by OpenAI into a Python dictionary
        return json.loads(content_string)
    else:
        print(f"OpenAI Error: {response.status_code} - {response.text}")
        return None

def get_youtube_thumbnail(search_query):
    """Calls the YouTube Data API to fetch the top video for a given query."""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    url = "https://www.googleapis.com/youtube/v3/search"
    
    params = {
        "part": "snippet",
        "q": search_query,
        "type": "video",
        "maxResults": 1,
        "key": api_key
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("items"):
            snippet = data["items"][0]["snippet"]
            return {
                "title": snippet["title"],
                "description": snippet["description"],
                "url": snippet["thumbnails"]["high"]["url"]
            }
    print(f"YouTube API Error or no results for query: '{search_query}'")
    return None

def build_daily_puzzle():
    """Orchestrates the APIs to build the final puzzle payload."""
    ai_data = generate_categories_with_openai()
    
    if not ai_data or "categories" not in ai_data:
        return None

    print("2. Calling YouTube API to fetch thumbnails for all 16 queries...")
    thumbnails = []
    id_counter = 1
    
    for category in ai_data["categories"]:
        cat_name = category["category_name"]
        for query in category["search_queries"]:
            yt_data = get_youtube_thumbnail(query)
            
            if yt_data:
                thumbnails.append({
                    "id": id_counter,
                    "url": yt_data["url"],
                    "title": yt_data["title"],
                    "description": yt_data["description"],
                    "category": cat_name
                })
                id_counter += 1
            else:
                # Fallback just in case a search fails, so the grid doesn't break
                thumbnails.append({
                    "id": id_counter,
                    "url": "https://via.placeholder.com/600x400?text=Video+Not+Found",
                    "title": "Fallback Video",
                    "description": "API limit reached or search failed.",
                    "category": cat_name
                })
                id_counter += 1
                
    # Shuffle the thumbnails so the puzzle isn't instantly solved
    print("3. Shuffling the puzzle pieces...")
    random.shuffle(thumbnails)
    
    return {"thumbnails": thumbnails}

# --- FLASK ROUTES ---
@app.route('/api/puzzle', methods=['GET'])
def get_puzzle():
    today = datetime.date.today()
    
    # 1. Check if today's puzzle is already in the database
    puzzle = DailyPuzzle.query.get(today)
    
    # 2. If not, generate the puzzle, save it, and then serve it
    if not puzzle:
        print(f"No puzzle found in database for {today}. Generating new one...")
        new_puzzle_data = build_daily_puzzle()
        
        if new_puzzle_data:
            new_puzzle = DailyPuzzle(puzzle_date=today, puzzle_data=new_puzzle_data)
            db.session.add(new_puzzle)
            db.session.commit()
            print("Puzzle successfully saved to the database!")
            puzzle = new_puzzle
        else:
            return jsonify({"error": "Failed to generate puzzle"}), 500
            
    # 3. Serve the cached JSON data to the frontend
    return jsonify(puzzle.puzzle_data)

if __name__ == '__main__':
    # Ensure the database tables are created before starting the app
    with app.app_context():
        db.create_all()
        
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)