import requests

YOUTUBE_API_KEY = "AIzaSyCaVj9a-f6khw38iXiih2kDgVH9AOZB8gc"

EMOTION_QUERIES = {
    "happy":    "productive study session motivation students",
    "sad":      "calm relaxing study music focus",
    "neutral":  "pomodoro study with me timer",
    "angry":    "breathing exercise stress relief students",
    "surprise": "quick concept revision tips students",
    "disgust":  "interactive learning techniques students",
    "fear":     "exam anxiety relief study tips",
}

_video_cache = {}

def get_study_videos(emotion, max_results=3):
    emotion = emotion.lower()

    if emotion in _video_cache:
        print(f"[YouTube] Using cached videos for '{emotion}'")
        return _video_cache[emotion]

    try:
        if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "YOUR_YOUTUBE_API_KEY_HERE":
            print("[YouTube] API key not set!")
            return _fallback_videos(emotion)

        query  = EMOTION_QUERIES.get(emotion, "study tips students")
        url    = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part":              "snippet",
            "q":                 query,
            "type":              "video",
            "maxResults":        max_results,
            "key":               YOUTUBE_API_KEY,
            "relevanceLanguage": "en",
            "safeSearch":        "strict",
        }

        print(f"[YouTube] Fetching for '{emotion}'...")
        response = requests.get(url, params=params, timeout=8)
        print(f"[YouTube Status] {response.status_code}")

        if response.status_code == 403:
            print("[YouTube] Quota exceeded — using fallback")
            return _fallback_videos(emotion)

        if response.status_code != 200:
            print(f"[YouTube Error] {response.text[:300]}")
            return _fallback_videos(emotion)

        data  = response.json()
        items = data.get("items", [])

        if not items:
            return _fallback_videos(emotion)

        videos = []
        for item in items:
            vid_id = item["id"]["videoId"]
            title  = item["snippet"]["title"]
            thumb  = item["snippet"]["thumbnails"]["medium"]["url"]
            videos.append({
                "title":     title,
                "url":       f"https://www.youtube.com/watch?v={vid_id}",
                "thumbnail": thumb,
                "embed":     f"https://www.youtube.com/embed/{vid_id}",
            })

        _video_cache[emotion] = videos
        return videos

    except Exception as e:
        print(f"[YouTube Exception] {e}")
        return _fallback_videos(emotion)


def _fallback_videos(emotion):
    fallbacks = {
        "happy": [
            {"title": "Study With Me — Productive Session",      "url": "https://www.youtube.com/watch?v=8ZpfPAGjwKY", "thumbnail": "https://img.youtube.com/vi/8ZpfPAGjwKY/mqdefault.jpg", "embed": "https://www.youtube.com/embed/8ZpfPAGjwKY"},
            {"title": "Upbeat Study Music for Focus",            "url": "https://www.youtube.com/watch?v=5qap5aO4i9A", "thumbnail": "https://img.youtube.com/vi/5qap5aO4i9A/mqdefault.jpg", "embed": "https://www.youtube.com/embed/5qap5aO4i9A"},
            {"title": "Deep Focus — 3 Hours Study Music",        "url": "https://www.youtube.com/watch?v=lTRiuFIWV54", "thumbnail": "https://img.youtube.com/vi/lTRiuFIWV54/mqdefault.jpg", "embed": "https://www.youtube.com/embed/lTRiuFIWV54"},
        ],
        "sad": [
            {"title": "Calm Study Music — Gentle Focus",         "url": "https://www.youtube.com/watch?v=77ZozI0rw7w", "thumbnail": "https://img.youtube.com/vi/77ZozI0rw7w/mqdefault.jpg", "embed": "https://www.youtube.com/embed/77ZozI0rw7w"},
            {"title": "Lofi Hip Hop — Relaxing Study Beats",     "url": "https://www.youtube.com/watch?v=5qap5aO4i9A", "thumbnail": "https://img.youtube.com/vi/5qap5aO4i9A/mqdefault.jpg", "embed": "https://www.youtube.com/embed/5qap5aO4i9A"},
            {"title": "Soft Piano Study Music",                  "url": "https://www.youtube.com/watch?v=lTRiuFIWV54", "thumbnail": "https://img.youtube.com/vi/lTRiuFIWV54/mqdefault.jpg", "embed": "https://www.youtube.com/embed/lTRiuFIWV54"},
        ],
        "angry": [
            {"title": "Box Breathing Exercise — Calm Down Fast", "url": "https://www.youtube.com/watch?v=tybOi4hjZFQ", "thumbnail": "https://img.youtube.com/vi/tybOi4hjZFQ/mqdefault.jpg", "embed": "https://www.youtube.com/embed/tybOi4hjZFQ"},
            {"title": "5 Min Meditation for Students",           "url": "https://www.youtube.com/watch?v=inpok4MKVLM", "thumbnail": "https://img.youtube.com/vi/inpok4MKVLM/mqdefault.jpg", "embed": "https://www.youtube.com/embed/inpok4MKVLM"},
            {"title": "Stress Relief Music — Study Calm",        "url": "https://www.youtube.com/watch?v=77ZozI0rw7w", "thumbnail": "https://img.youtube.com/vi/77ZozI0rw7w/mqdefault.jpg", "embed": "https://www.youtube.com/embed/77ZozI0rw7w"},
        ],
        "neutral": [
            {"title": "Pomodoro Timer — 25 Min Study Session",   "url": "https://www.youtube.com/watch?v=mNBmG24djoY", "thumbnail": "https://img.youtube.com/vi/mNBmG24djoY/mqdefault.jpg", "embed": "https://www.youtube.com/embed/mNBmG24djoY"},
            {"title": "Study With Me — 2 Hour Session",          "url": "https://www.youtube.com/watch?v=8ZpfPAGjwKY", "thumbnail": "https://img.youtube.com/vi/8ZpfPAGjwKY/mqdefault.jpg", "embed": "https://www.youtube.com/embed/8ZpfPAGjwKY"},
            {"title": "Lo-fi Beats to Study and Relax",          "url": "https://www.youtube.com/watch?v=5qap5aO4i9A", "thumbnail": "https://img.youtube.com/vi/5qap5aO4i9A/mqdefault.jpg", "embed": "https://www.youtube.com/embed/5qap5aO4i9A"},
        ],
        "surprise": [
            {"title": "Quick Revision Tips — Study Smarter",     "url": "https://www.youtube.com/watch?v=IlU-zDU6aQ0", "thumbnail": "https://img.youtube.com/vi/IlU-zDU6aQ0/mqdefault.jpg", "embed": "https://www.youtube.com/embed/IlU-zDU6aQ0"},
            {"title": "Active Recall — Best Study Technique",    "url": "https://www.youtube.com/watch?v=ukLnPbIffxE", "thumbnail": "https://img.youtube.com/vi/ukLnPbIffxE/mqdefault.jpg", "embed": "https://www.youtube.com/embed/ukLnPbIffxE"},
            {"title": "Spaced Repetition Explained",             "url": "https://www.youtube.com/watch?v=Z-zNHHpXoMM", "thumbnail": "https://img.youtube.com/vi/Z-zNHHpXoMM/mqdefault.jpg", "embed": "https://www.youtube.com/embed/Z-zNHHpXoMM"},
        ],
        "disgust": [
            {"title": "How to Stay Motivated to Study",          "url": "https://www.youtube.com/watch?v=75d_29QWELk", "thumbnail": "https://img.youtube.com/vi/75d_29QWELk/mqdefault.jpg", "embed": "https://www.youtube.com/embed/75d_29QWELk"},
            {"title": "Study Techniques That Actually Work",     "url": "https://www.youtube.com/watch?v=IlU-zDU6aQ0", "thumbnail": "https://img.youtube.com/vi/IlU-zDU6aQ0/mqdefault.jpg", "embed": "https://www.youtube.com/embed/IlU-zDU6aQ0"},
            {"title": "Lofi Chill Beats — Reset Your Mind",      "url": "https://www.youtube.com/watch?v=5qap5aO4i9A", "thumbnail": "https://img.youtube.com/vi/5qap5aO4i9A/mqdefault.jpg", "embed": "https://www.youtube.com/embed/5qap5aO4i9A"},
        ],
        "fear": [
            {"title": "Overcome Exam Anxiety — Practical Tips",  "url": "https://www.youtube.com/watch?v=75d_29QWELk", "thumbnail": "https://img.youtube.com/vi/75d_29QWELk/mqdefault.jpg", "embed": "https://www.youtube.com/embed/75d_29QWELk"},
            {"title": "Breathing Exercise for Exam Stress",      "url": "https://www.youtube.com/watch?v=tybOi4hjZFQ", "thumbnail": "https://img.youtube.com/vi/tybOi4hjZFQ/mqdefault.jpg", "embed": "https://www.youtube.com/embed/tybOi4hjZFQ"},
            {"title": "Study Music — Stay Calm and Focused",     "url": "https://www.youtube.com/watch?v=lTRiuFIWV54", "thumbnail": "https://img.youtube.com/vi/lTRiuFIWV54/mqdefault.jpg", "embed": "https://www.youtube.com/embed/lTRiuFIWV54"},
        ],
    }
    return fallbacks.get(emotion, fallbacks["neutral"])