import requests

def get_motivational_quote(emotion):
    try:
        response = requests.get(
            "https://zenquotes.io/api/random",
            timeout=5
        )
        data = response.json()
        quote  = data[0]["q"]
        author = data[0]["a"]
        return {"quote": quote, "author": author}

    except Exception as e:
        print(f"[Quotes API Error] {e}")
        return {
            "quote": "Every expert was once a beginner.",
            "author": "Unknown"
        }