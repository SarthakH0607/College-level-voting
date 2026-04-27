"""
Unit Tests for BiometricController
Tests all rule paths per the strict verification spec.
"""
import unittest
from unittest.mock import MagicMock, patch
from biometric_controller import BiometricController, FACE_SIMILARITY_THRESHOLD, VOICE_CONFIDENCE_THRESHOLD


class TestFaceVerification(unittest.TestCase):
    def setUp(self):
        self.face_verifier = MagicMock()
        self.ctrl = BiometricController(face_verifier=self.face_verifier)
        self.session = 'test-session-001'
        self.voter = 'voter-123'

    def test_camera_off_fails(self):
        r = self.ctrl.verify_face(self.voter, 'img', False, True, self.session)
        self.assertEqual(r['status'], 'FAILED')
        self.assertIn('Camera is off', r['reason'])

    def test_camera_null_fails(self):
        r = self.ctrl.verify_face(self.voter, 'img', None, True, self.session)
        self.assertEqual(r['status'], 'FAILED')
        self.assertIn('Camera is off', r['reason'])

    def test_no_face_detected_fails(self):
        r = self.ctrl.verify_face(self.voter, 'img', True, False, self.session)
        self.assertEqual(r['status'], 'FAILED')
        self.assertIn('No face detected', r['reason'])

    def test_face_detected_null_fails(self):
        r = self.ctrl.verify_face(self.voter, 'img', True, None, self.session)
        self.assertEqual(r['status'], 'FAILED')
        self.assertIn('No face detected', r['reason'])

    def test_low_similarity_fails(self):
        self.face_verifier.verify.return_value = {'verified': False, 'confidence': 0.50}
        r = self.ctrl.verify_face(self.voter, 'img', True, True, self.session)
        self.assertEqual(r['status'], 'FAILED')
        self.assertIn('does not match', r['reason'])

    def test_high_similarity_passes(self):
        self.face_verifier.verify.return_value = {'verified': True, 'confidence': 0.85}
        r = self.ctrl.verify_face(self.voter, 'img', True, True, self.session)
        self.assertEqual(r['status'], 'VERIFIED')
        self.assertAlmostEqual(r['similarity_score'], 0.85, places=2)

    def test_threshold_boundary_passes(self):
        self.face_verifier.verify.return_value = {'verified': True, 'confidence': 0.65}
        r = self.ctrl.verify_face(self.voter, 'img', True, True, self.session)
        self.assertEqual(r['status'], 'VERIFIED')

    def test_threshold_just_below_fails(self):
        self.face_verifier.verify.return_value = {'verified': False, 'confidence': 0.649}
        r = self.ctrl.verify_face(self.voter, 'img', True, True, self.session)
        self.assertEqual(r['status'], 'FAILED')

    def test_missing_session_fails(self):
        r = self.ctrl.verify_face(self.voter, 'img', True, True, '')
        self.assertEqual(r['status'], 'FAILED')
        self.assertIn('session', r['reason'].lower())

    def test_no_verifier_fails(self):
        ctrl = BiometricController(face_verifier=None)
        r = ctrl.verify_face(self.voter, 'img', True, True, self.session)
        self.assertEqual(r['status'], 'FAILED')
        self.assertIn('unavailable', r['reason'])


class TestVoiceVerification(unittest.TestCase):
    def setUp(self):
        self.voice_verifier = MagicMock()
        self.ctrl = BiometricController(voice_verifier=self.voice_verifier)
        self.session = 'test-session-002'
        self.voter = 'voter-456'

    def test_mic_off_fails(self):
        r = self.ctrl.verify_voice(self.voter, '/audio', 'phrase', False, True, self.session)
        self.assertEqual(r['status'], 'FAILED')
        self.assertIn('Microphone is off', r['reason'])

    def test_mic_null_fails(self):
        r = self.ctrl.verify_voice(self.voter, '/audio', 'phrase', None, True, self.session)
        self.assertEqual(r['status'], 'FAILED')
        self.assertIn('Microphone is off', r['reason'])

    def test_silent_audio_fails(self):
        r = self.ctrl.verify_voice(self.voter, '/audio', 'phrase', True, False, self.session)
        self.assertEqual(r['status'], 'FAILED')
        self.assertIn('No voice detected', r['reason'])

    def test_silent_null_fails(self):
        r = self.ctrl.verify_voice(self.voter, '/audio', 'phrase', True, None, self.session)
        self.assertEqual(r['status'], 'FAILED')
        self.assertIn('No voice detected', r['reason'])

    def test_low_confidence_fails(self):
        self.voice_verifier.verify.return_value = {
            'verified': False, 'speakerMatch': False, 'transcriptMatch': False,
            'speakerSimilarity': 0.3, 'transcriptConfidence': 0.2
        }
        r = self.ctrl.verify_voice(self.voter, '/audio', 'phrase', True, True, self.session)
        self.assertEqual(r['status'], 'FAILED')

    def test_high_confidence_passes(self):
        self.voice_verifier.verify.return_value = {
            'verified': True, 'speakerMatch': True, 'transcriptMatch': True,
            'speakerSimilarity': 0.9, 'transcriptConfidence': 0.95
        }
        r = self.ctrl.verify_voice(self.voter, '/audio', 'phrase', True, True, self.session)
        self.assertEqual(r['status'], 'VERIFIED')

    def test_no_verifier_fails(self):
        ctrl = BiometricController(voice_verifier=None)
        r = ctrl.verify_voice(self.voter, '/audio', 'phrase', True, True, self.session)
        self.assertEqual(r['status'], 'FAILED')
        self.assertIn('unavailable', r['reason'])


class TestAuthorization(unittest.TestCase):
    def setUp(self):
        self.ctrl = BiometricController()

    def test_both_verified_grants_access(self):
        face = {'status': 'VERIFIED', 'similarity_score': 0.9}
        voice = {'status': 'VERIFIED', 'confidence_score': 0.85}
        r = self.ctrl.authorize_vote('v1', 'sess1', face, voice)
        self.assertEqual(r['combined_status'], 'ACCESS GRANTED')

    def test_face_failed_denies(self):
        face = {'status': 'FAILED', 'reason': 'No match'}
        voice = {'status': 'VERIFIED', 'confidence_score': 0.85}
        r = self.ctrl.authorize_vote('v1', 'sess1', face, voice)
        self.assertEqual(r['combined_status'], 'ACCESS DENIED')

    def test_voice_failed_denies(self):
        face = {'status': 'VERIFIED', 'similarity_score': 0.9}
        voice = {'status': 'FAILED', 'reason': 'No match'}
        r = self.ctrl.authorize_vote('v1', 'sess1', face, voice)
        self.assertEqual(r['combined_status'], 'ACCESS DENIED')

    def test_both_failed_denies(self):
        face = {'status': 'FAILED', 'reason': 'No match'}
        voice = {'status': 'FAILED', 'reason': 'No match'}
        r = self.ctrl.authorize_vote('v1', 'sess1', face, voice)
        self.assertEqual(r['combined_status'], 'ACCESS DENIED')

    def test_missing_session_denies(self):
        face = {'status': 'VERIFIED'}
        voice = {'status': 'VERIFIED'}
        r = self.ctrl.authorize_vote('v1', '', face, voice)
        self.assertEqual(r['combined_status'], 'ACCESS DENIED')


class TestAuditLogging(unittest.TestCase):
    def test_failed_attempts_logged(self):
        ctrl = BiometricController()
        ctrl.verify_face('v1', 'img', False, True, 'sess')
        ctrl.verify_face('v1', 'img', True, False, 'sess')
        logs = ctrl.get_failed_attempts(voter_id='v1')
        self.assertEqual(len(logs), 2)

    def test_filter_by_voter(self):
        ctrl = BiometricController()
        ctrl.verify_face('v1', 'img', False, True, 's1')
        ctrl.verify_face('v2', 'img', False, True, 's2')
        self.assertEqual(len(ctrl.get_failed_attempts(voter_id='v1')), 1)


if __name__ == '__main__':
    unittest.main()
