import os
import requests

def load_secrets():
    """Reads secrets.txt and loads them into environment variables."""
    try:
        with open("secrets.txt", "r") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        print("Error: secrets.txt not found! Make sure you are in the right folder.")
        return False
    return True

def test_youtube_api():
    print("1. Loading API key...")
    if not load_secrets():
        return
        
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("Error: YOUTUBE_API_KEY not found in secrets.txt")
        return

    print("2. Key loaded successfully! Connecting to YouTube...")
    url = "https://www.googleapis.com/youtube/v3/search"
    
    # We will use a fun test query
    params = {
        "part": "snippet",
        "q": "Carnegie Mellon University campus tour",
        "type": "video",
        "maxResults": 1,
        "key": api_key
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("items"):
            video = data["items"][0]["snippet"]
            print("\n✅ SUCCESS! Your API key works perfectly.")
            print(f"Video Title: {video['title']}")
            print(f"Channel: {video['channelTitle']}")
            print(f"Thumbnail URL: {video['thumbnails']['high']['url']}")
        else:
            print("\n⚠️ The API connected, but no videos were found for that query.")
    else:
        print(f"\n❌ ERROR {response.status_code}: The API request failed.")
        print(response.json())

if __name__ == "__main__":
    test_youtube_api()