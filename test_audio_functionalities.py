import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, request, jsonify
from app import app, transcribe, tts

class AudioFunctionalityTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_audio_recording(self):
        # Test audio recording functionality
        with patch('app.MediaRecorder') as MockMediaRecorder:
            mock_recorder = MockMediaRecorder.return_value
            mock_recorder.start = MagicMock()
            mock_recorder.stop = MagicMock()
    
            # Simulate recording
            response = self.app.post('/record_audio', data={'action': 'start'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'recording_started')
    
            # Simulate stopping recording
            response = self.app.post('/record_audio', data={'action': 'stop'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['status'], 'recording_stopped')
    
            # Verify that start and stop were called
            mock_recorder.start.assert_called_once()
            mock_recorder.stop.assert_called_once()

    def test_audio_transcription(self):
        # Test audio transcription functionality
        with patch('app.sr.Recognizer') as MockRecognizer:
            mock_recognizer = MockRecognizer.return_value
            mock_recognizer.record = MagicMock()
            mock_recognizer.recognize_google = MagicMock(return_value="test transcription")
    
            # Simulate audio file upload
            with open('test_audio.wav', 'rb') as f:
                response = self.app.post('/transcribe', data={'audio': f})
    
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['text'], "test transcription")
            self.assertEqual(response.json['status'], 'success')

    def test_text_to_speech(self):
        # Test text-to-speech functionality
        with patch('app.pyttsx3') as MockPyttsx3:
            mock_engine = MockPyttsx3.init.return_value
            mock_engine.save_to_file = MagicMock()
            mock_engine.runAndWait = MagicMock()
    
            # Simulate TTS request
            response = self.app.post('/tts', json={'text': 'Hello, world!'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['Content-Type'], 'audio/wav')
    
            # Verify that save_to_file and runAndWait were called
            mock_engine.save_to_file.assert_called_once_with('Hello, world!', mock.ANY)
            mock_engine.runAndWait.assert_called_once()

if __name__ == '__main__':
    unittest.main()