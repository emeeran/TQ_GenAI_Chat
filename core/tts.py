"""
Text-to-Speech Module

Handles text-to-speech conversion with multiple engine support.
"""

import os
import tempfile

import logging

# Optional TTS imports
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    from gtts import gTTS
except ImportError:
    gTTS = None


class TTSVoice:
    """Represents a TTS voice option"""

    def __init__(self, voice_id: str, name: str, lang: str = "", gender: str = ""):
        self.id = voice_id
        self.name = name
        self.lang = lang
        self.gender = gender

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "lang": self.lang,
            "gender": self.gender,
        }


class TTSEngine:
    """Text-to-Speech engine interface"""

    def get_voices(self) -> list[TTSVoice]:
        """Get available voices"""
        voices = []

        # Add pyttsx3 voices if available
        if pyttsx3:
            try:
                engine = pyttsx3.init()
                for voice in engine.getProperty("voices"):
                    voices.append(
                        TTSVoice(
                            voice_id=voice.id,
                            name=voice.name,
                            lang=voice.languages[0] if voice.languages else "",
                            gender=getattr(voice, "gender", ""),
                        )
                    )
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to get pyttsx3 voices: {e}")

        # Add gTTS voice if available
        if gTTS:
            voices.append(TTSVoice(voice_id="gtts", name="Google TTS", lang="en", gender=""))

        return voices

    def synthesize(
        self, text: str, voice_id: str | None = None, lang: str = "en"
    ) -> tuple[bytes, str]:
        """
        Synthesize text to speech

        Returns:
            tuple: (audio_data, content_type)
        """
        if not text:
            raise ValueError("No text provided")

        # Try pyttsx3 first
        if pyttsx3:
            try:
                return self._synthesize_pyttsx3(text, voice_id)
            except Exception as e:
                logging.getLogger(__name__).warning(f"pyttsx3 synthesis failed: {e}")

        # Fallback to gTTS
        if gTTS:
            try:
                return self._synthesize_gtts(text, lang)
            except Exception as e:
                logging.getLogger(__name__).error(f"gTTS synthesis failed: {e}")
                raise ValueError(f"gTTS error: {str(e)}") from e

        raise ValueError("No TTS engine available. Please install pyttsx3 or gTTS.")

    def _synthesize_pyttsx3(self, text: str, voice_id: str | None) -> tuple[bytes, str]:
        """Synthesize using pyttsx3"""
        engine = pyttsx3.init()

        if voice_id:
            try:
                engine.setProperty("voice", voice_id)
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to set voice {voice_id}: {e}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf:
            try:
                engine.save_to_file(text, tf.name)
                engine.runAndWait()

                with open(tf.name, "rb") as audio_file:
                    audio_data = audio_file.read()

                return audio_data, "audio/wav"
            finally:
                try:
                    os.unlink(tf.name)
                except OSError:
                    pass

    def _synthesize_gtts(self, text: str, lang: str) -> tuple[bytes, str]:
        """Synthesize using gTTS"""
        tts = gTTS(text=text, lang=lang)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tf:
            try:
                tts.save(tf.name)

                with open(tf.name, "rb") as audio_file:
                    audio_data = audio_file.read()

                return audio_data, "audio/mpeg"
            finally:
                try:
                    os.unlink(tf.name)
                except OSError:
                    pass


# Global TTS engine instance
tts_engine = TTSEngine()
