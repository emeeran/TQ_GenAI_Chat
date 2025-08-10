from flask import Blueprint, request, jsonify
from core.tts import tts_engine

tts_bp = Blueprint("tts", __name__, url_prefix="/api/tts")

@tts_bp.route("/voices", methods=["GET"])
def tts_voices():
    try:
        voices = tts_engine.get_voices()
        return jsonify({"voices": [voice.to_dict() for voice in voices]})
    except Exception as e:
        return jsonify({"error": "Failed to get TTS voices"}), 500

@tts_bp.route("/", methods=["POST"])
def tts():
    try:
        data = request.get_json()
        text = data.get("text", "")
        voice_id = data.get("voice_id")
        lang = data.get("lang", "en")
        if not text:
            return jsonify({"error": "No text provided"}), 400
        audio_data, content_type = tts_engine.synthesize(text, voice_id, lang)
        return audio_data, 200, {"Content-Type": content_type}
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "TTS processing failed"}), 500
