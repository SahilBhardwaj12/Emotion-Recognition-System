EMOTION_DATA = {
    "happy": {
        "message": "Great mood! Perfect time for challenging problems.",
        "tips": [
            "Tackle your hardest subject while energy is high.",
            "Try a new topic or advance to the next chapter.",
            "Help a classmate — teaching reinforces your own knowledge."
        ],
        "video_query": "advanced study techniques motivation"
    },
    "sad": {
        "message": "It's okay to feel sad. Take it slow.",
        "tips": [
            "Take a 10-minute break before continuing.",
            "Listen to calm, instrumental music.",
            "Review easier material to rebuild momentum."
        ],
        "video_query": "calm study music focus"
    },
    "angry": {
        "message": "Take a breath. A calm mind learns better.",
        "tips": [
            "Step away for 5 minutes and breathe deeply.",
            "Write down what's frustrating you, then set it aside.",
            "Switch to a lighter topic temporarily."
        ],
        "video_query": "relaxing study music stress relief"
    },
    "fear": {
        "message": "Fear is normal. Start small and build up.",
        "tips": [
            "Break the topic into smaller, manageable pieces.",
            "Review fundamentals to rebuild confidence.",
            "Remember: confusion is part of the learning process."
        ],
        "video_query": "study confidence tips beginners"
    },
    "surprise": {
        "message": "Something caught you off guard — revisit it!",
        "tips": [
            "Re-read the section that surprised you.",
            "Make a note to research this topic further.",
            "Connect this new info to what you already know."
        ],
        "video_query": "deep learning understanding concepts"
    },
    "disgust": {
        "message": "Not feeling it? That's fine — reset your mindset.",
        "tips": [
            "Take a short walk or stretch break.",
            "Switch to a subject you enjoy temporarily.",
            "Remind yourself of your long-term goal."
        ],
        "video_query": "study motivation mindset tips"
    },
    "neutral": {
        "message": "Solid focus state — keep the momentum going.",
        "tips": [
            "This is your prime study window — use it well.",
            "Try the Pomodoro technique: 25 min on, 5 min off.",
            "Set a specific goal for the next 30 minutes."
        ],
        "video_query": "productive study session focus techniques"
    }
}

def get_recommendation(emotion: str) -> dict:
    key = emotion.lower() if emotion else ""
    data = EMOTION_DATA.get(key)

    if data:
        return {
            "message": data["message"],
            "tips":    data["tips"],
            "video_query": data["video_query"]
        }

    return {
        "message":     "Stay focused and keep studying!",
        "tips":        ["Set clear goals.", "Take regular breaks.", "Stay hydrated."],
        "video_query": "study tips productivity"
    }