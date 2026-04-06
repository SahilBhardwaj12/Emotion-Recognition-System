import requests
import json
import time

GEMINI_API_KEY = "AIzaSyAYqlAP4GAiL1Ai6Qg27mW3ZgyLgAusFoM"

# gemini-2.0-flash-lite has free tier quota available
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.0-flash-lite:generateContent?key={GEMINI_API_KEY}"
)

# Rate limiting — don't call more than once every 30 seconds
_last_call_time = 0
_cached_advice  = {}   # cache advice per emotion so we don't re-call

def get_ai_study_advice(emotion, confidence):
    global _last_call_time

    # Return cached advice if same emotion called recently
    if emotion in _cached_advice:
        return _cached_advice[emotion]

    # Rate limit — wait if called too recently
    elapsed = time.time() - _last_call_time
    if elapsed < 30:
        return _cached_advice.get(emotion, "Generating advice — please wait a moment…")

    try:
        prompt = f"""You are a friendly student study assistant.
A student's emotion was detected as '{emotion}' with {confidence:.0%} confidence.
Give a short, warm response with:
1. One sentence acknowledging their emotional state
2. Three bullet point study tips suited to this emotion
3. One motivational closing line
Keep it under 80 words. Be encouraging."""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        headers = {"Content-Type": "application/json"}

        response = requests.post(
            GEMINI_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=10
        )

        print(f"[Gemini Status] {response.status_code}")

        if response.status_code == 429:
            print("[Gemini] Quota hit — using cached/fallback advice")
            return _get_fallback_advice(emotion)

        if response.status_code != 200:
            print(f"[Gemini Error] {response.text[:200]}")
            return _get_fallback_advice(emotion)

        result = response.json()
        text   = result["candidates"][0]["content"]["parts"][0]["text"].strip()

        _cached_advice[emotion] = text
        _last_call_time = time.time()
        return text

    except Exception as e:
        print(f"[Gemini API Error] {e}")
        return _get_fallback_advice(emotion)
    
def get_chat_response(message, emotion, confidence):
    try:
        prompt = f"""You are EmoStudyAI — a friendly student study assistant chatbot.
Current detected emotion: {emotion} ({confidence:.1f}% confidence)

Student says: "{message}"

Reply helpfully in 2-3 sentences max. Be warm, encouraging, and study-focused."""

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}
        response = requests.post(GEMINI_URL, headers=headers,
                                 data=json.dumps(payload), timeout=10)
        if response.status_code != 200:
            return _get_fallback_advice(emotion)
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[Chat error] {e}")
        return "I'm here to help! Try focusing on one topic at a time."    


def _get_fallback_advice(emotion):
    """Shown when API quota is exceeded."""
    fallback = {
        "happy":    "You're in great shape! Tackle your hardest topic now, attempt difficult problems, and set ambitious goals. You've got this!",
        "sad":      "It's okay to feel low. Start with easy revision, watch a short concept video, and take a gentle 5-minute break. Small steps matter.",
        "neutral":  "You're calm and steady — perfect for focused study. Stick to your plan, revise notes, and try the Pomodoro technique.",
        "angry":    "Take a short pause and breathe. Switch to an easier topic first, then return when you feel calmer. You've got this.",
        "surprise": "You seem alert! Use this energy for a quick concept quiz or active recall. Great time for short, sharp revision.",
        "disgust":  "Try switching subjects or study method. Interactive or visual learning might help refresh your focus right now.",
        "fear":     "Break it into tiny steps. Start with what you already know. Progress over perfection — every bit counts.",
    }
    return fallback.get(emotion, "Stay focused and keep going — every study session brings you closer to your goal.")