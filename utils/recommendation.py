def get_recommendation(emotion):

    recommendations = {

        "happy": {
            "title": "High Productivity Mode",
            "tips": [
                "Attempt difficult problems",
                "Start a new topic",
                "Solve practice questions"
            ]
        },

        "sad": {
            "title": "Light Study Mode",
            "tips": [
                "Revise an easy topic",
                "Watch a short concept video",
                "Take a short break"
            ]
        },

        "neutral": {
            "title": "Balanced Study Mode",
            "tips": [
                "Continue normal study",
                "Revise notes",
                "Solve moderate questions"
            ]
        },

        "angry": {
            "title": "Calm Reset Mode",
            "tips": [
                "Take deep breaths",
                "Pause for 3 minutes",
                "Switch to an easier topic"
            ]
        },

        "surprise": {
            "title": "Quick Concept Check",
            "tips": [
                "Review key concepts",
                "Attempt a quick quiz",
                "Test your understanding"
            ]
        },

        "disgust": {
            "title": "Refresh Mode",
            "tips": [
                "Change subject",
                "Clean study space",
                "Try interactive learning"
            ]
        }

    }

    return recommendations.get(emotion, {})