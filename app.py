import os
import json
import datetime
import random
from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
# Allow the frontend to communicate with this backend
CORS(app)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///local_puzzles.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Model
class DailyPuzzle(db.Model):
    __tablename__ = 'daily_puzzles'
    puzzle_date = db.Column(db.Date, primary_key=True)
    puzzle_data = db.Column(db.JSON, nullable=False)

def generate_mock_puzzle():
    """
    Mock function representing your OpenAI and YouTube API calls.
    Returns a shuffled list of 16 thumbnails across 4 categories.
    """
    categories = ["Tech Tutorials", "Baking", "Theme Parks", "Music Videos"]
    thumbnails = []
    
    # Generate 4 mock items per category
    id_counter = 1
    for cat in categories:
        for i in range(4):
            thumbnails.append({
                "id": id_counter,
                "url": f"https://picsum.photos/seed/{id_counter}/600/400", # Placeholder images
                "title": f"Mock Video {id_counter}",
                "description": f"This is a mock description for a {cat} video.",
                "category": cat
            })
            id_counter += 1
            
    # Shuffle the list so the puzzle is scrambled
    random.shuffle(thumbnails)
    return {"thumbnails": thumbnails}

@app.route('/api/puzzle', methods=['GET'])
def get_puzzle():
    today = datetime.date.today()
    
    # 1. Try to fetch today's puzzle from the database
    puzzle = DailyPuzzle.query.get(today)
    
    # 2. If it doesn't exist, generate it, save it, and then serve it
    if not puzzle:
        print(f"Generating new puzzle for {today}...")
        new_data = generate_mock_puzzle()
        new_puzzle = DailyPuzzle(puzzle_date=today, puzzle_data=new_data)
        db.session.add(new_puzzle)
        db.session.commit()
        puzzle = new_puzzle
        
    # 3. Return the JSON data to the frontend
    return jsonify(puzzle.puzzle_data)

if __name__ == '__main__':
    # Ensure the database tables are created before starting the app
    with app.app_context():
        db.create_all()
        
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)