import requests
import json
import time

GEMINI_API_KEY = "AIzaSyAYqlAP4GAiL1Ai6Qg27mW3ZgyLgAusFoM"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash-lite:generateContent?key=" + GEMINI_API_KEY
)

_last_call_time = 0
_cached_advice  = {}
_chat_history   = []

def get_ai_study_advice(emotion, confidence):
    global _last_call_time
    if emotion in _cached_advice:
        return _cached_advice[emotion]
    elapsed = time.time() - _last_call_time
    if elapsed < 30:
        return _cached_advice.get(emotion, "Generating advice — please wait a moment…")
    try:
        prompt = (
            f"You are a friendly student study assistant. "
            f"A student's emotion was detected as '{emotion}' with {confidence:.0%} confidence. "
            f"Give a short warm response with: 1 sentence acknowledging their state, "
            f"3 bullet study tips for this emotion, 1 motivational closing line. "
            f"Under 80 words. Be encouraging."
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {"Content-Type": "application/json"}
        response = requests.post(GEMINI_URL, headers=headers, data=json.dumps(payload), timeout=10)
        print(f"[Gemini Status] {response.status_code}")
        if response.status_code == 429:
            return _get_fallback_advice(emotion)
        if response.status_code != 200:
            return _get_fallback_advice(emotion)
        result = response.json()
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        _cached_advice[emotion] = text
        _last_call_time = time.time()
        return text
    except Exception as e:
        print(f"[Gemini API Error] {e}")
        return _get_fallback_advice(emotion)


def get_chat_response(message, emotion, confidence):
    global _chat_history
    try:
        contents = []
        if not _chat_history:
            contents.append({"role": "user", "parts": [{"text": f"You are EmoStudyAI — a friendly student study assistant. Student emotion: {emotion} ({confidence:.1f}% confidence). Be warm, helpful, study-focused. Keep replies under 3 sentences."}]})
            contents.append({"role": "model", "parts": [{"text": "Hi! I'm your EmoStudyAI assistant. I can see how you're feeling and I'm here to help you study better. What's on your mind?"}]})
        contents.extend(_chat_history)
        contents.append({"role": "user", "parts": [{"text": message}]})

        payload = {"contents": contents}
        headers = {"Content-Type": "application/json"}
        response = requests.post(GEMINI_URL, headers=headers, data=json.dumps(payload), timeout=10)

        if response.status_code == 429:
            return _get_chat_fallback(emotion, message)
        if response.status_code != 200:
            return _get_chat_fallback(emotion, message)

        result = response.json()
        reply = result["candidates"][0]["content"]["parts"][0]["text"].strip()

        _chat_history.append({"role": "user",  "parts": [{"text": message}]})
        _chat_history.append({"role": "model", "parts": [{"text": reply}]})
        if len(_chat_history) > 10:
            _chat_history = _chat_history[-10:]

        return reply
    except Exception as e:
        print(f"[Chat error] {e}")
        return _get_chat_fallback(emotion, message)


def _get_chat_fallback(emotion, message):
    msg = message.lower()
    if any(w in msg for w in ['tired', 'stress', 'anxious', 'worry']):
        return "Take a deep breath! Short breaks every 25 minutes help a lot. You're doing great — keep going one step at a time."
    if any(w in msg for w in ['how', 'study', 'learn', 'remember']):
        return "Try the Pomodoro technique: 25 mins focused study, 5 min break. Active recall and spaced repetition are the most effective methods!"
    if any(w in msg for w in ['motivat', 'give up', 'can\'t']):
        return "Every expert was once a beginner. Break your goal into tiny steps and celebrate small wins. You've got this!"
    fallbacks = {
        "happy":   "You're in great energy! Use it to tackle your hardest topic first.",
        "sad":     "It's okay to feel low. Start with easy revision to build momentum.",
        "neutral": "Perfect focus state! Stick to your plan and try the Pomodoro method.",
        "angry":   "Take 5 deep breaths first. Then switch to an easy topic to reset.",
        "fear":    "Break it into tiny steps. Start with what you already know well.",
        "disgust": "Switch subjects or study method for a fresh perspective.",
        "surprise":"Use this alert energy for a quick concept quiz or active recall.",
    }
    return fallbacks.get(emotion, "Stay focused — every study session brings you closer to your goal!")


def _get_fallback_advice(emotion):
    fallback = {
        "happy":   "You're in great shape! Tackle your hardest topic now and set ambitious goals. You've got this!",
        "sad":     "It's okay to feel low. Start with easy revision, take a gentle break. Small steps matter.",
        "neutral": "You're calm and steady — perfect for focused study. Try the Pomodoro technique.",
        "angry":   "Take a short pause and breathe. Switch to an easier topic first. You've got this.",
        "surprise":"You seem alert! Use this energy for a quick concept quiz or active recall.",
        "disgust": "Try switching subjects or study method. Interactive learning might help refresh your focus.",
        "fear":    "Break it into tiny steps. Start with what you already know. Progress over perfection.",
    }
    return fallback.get(emotion, "Stay focused and keep going — every study session brings you closer to your goal.")