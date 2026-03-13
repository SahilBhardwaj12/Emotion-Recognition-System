import requests

API_KEY = "YOUR_YOUTUBE_API_KEY"

def get_study_videos(query):

    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": query,
        "key": API_KEY,
        "maxResults": 3,
        "type": "video"
    }

    response = requests.get(url, params=params)

    data = response.json()

    videos = []

    for item in data["items"]:

        video_id = item["id"]["videoId"]

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        videos.append(video_url)

    return videos
