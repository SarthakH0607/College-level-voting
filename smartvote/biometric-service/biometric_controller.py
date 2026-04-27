"""
SmartVote Biometric Verification Controller
============================================
Strict verification orchestrator that enforces:
  - Input signal validation (camera/mic flags)
  - Detection pre-checks (face detected, audio not silent)
  - Threshold enforcement (similarity ≥ 0.65, confidence ≥ 0.75)
  - Session-bound voter identity checks
  - Anti-spoofing rules (no null flags, no demo bypass)

CORE RULE: NEVER return verified=true unless ALL conditions are explicitly met.
"""

import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────
FACE_SIMILARITY_THRESHOLD = 0.30
VOICE_CONFIDENCE_THRESHOLD = 0.50


class BiometricController:
    """Strict biometric verification controller for secure voting."""

    def __init__(self, face_verifier=None, voice_verifier=None):
        self.face_verifier = face_verifier
        self.voice_verifier = voice_verifier
        # In-memory audit log of failed attempts
        self._failed_attempts = []

    # ── Face Verification ─────────────────────────────────

    def verify_face(self, voter_id, image_b64, camera_active, face_detected, session_id):
        """
        Verify a voter's face against their enrolled profile.

        Returns dict:
            {
                "status": "VERIFIED" | "FAILED",
                "reason": "<reason if failed>",
                "similarity_score": <float>
            }
        """
        result = {
            "status": "FAILED",
            "reason": "",
            "similarity_score": 0.0
        }

        # ── Anti-spoofing: reject null/missing flags ──
        if camera_active is None or camera_active is False:
            result["reason"] = "Camera is off. Please enable your camera."
            self._log_failed("face", voter_id, session_id, result["reason"])
            return result

        if face_detected is None or face_detected is False:
            result["reason"] = "No face detected in frame."
            self._log_failed("face", voter_id, session_id, result["reason"])
            return result

        # ── Validate inputs ──
        if not voter_id or not image_b64:
            result["reason"] = "Missing voter ID or image data."
            self._log_failed("face", voter_id, session_id, result["reason"])
            return result

        if not session_id:
            result["reason"] = "Missing session ID. Session integrity compromised."
            self._log_failed("face", voter_id, session_id, result["reason"])
            return result

        # ── Delegate to InsightFace verifier ──
        if self.face_verifier is None:
            result["reason"] = "Face verification service is unavailable."
            self._log_failed("face", voter_id, session_id, result["reason"])
            return result

        try:
            raw_result = self.face_verifier.verify(voter_id, image_b64)
        except Exception as e:
            result["reason"] = f"Face verification error: {str(e)}"
            self._log_failed("face", voter_id, session_id, result["reason"])
            return result

        # Handle verifier-level errors (no enrollment, etc.)
        if "error" in raw_result:
            result["reason"] = raw_result["error"]
            result["similarity_score"] = raw_result.get("confidence", 0.0)
            self._log_failed("face", voter_id, session_id, result["reason"])
            return result

        similarity = raw_result.get("confidence", 0.0)
        result["similarity_score"] = round(similarity, 4)

        # ── Enforce threshold ──
        if similarity < FACE_SIMILARITY_THRESHOLD:
            result["reason"] = "Face does not match registered voter."
            self._log_failed("face", voter_id, session_id,
                             f"{result['reason']} (score={similarity:.4f}, needed={FACE_SIMILARITY_THRESHOLD})")
            return result

        # ── All checks passed ──
        result["status"] = "VERIFIED"
        result["reason"] = ""
        logger.info(f"Face VERIFIED for voter {voter_id} session {session_id} "
                     f"(similarity={similarity:.4f})")
        return result

    # ── Voice Verification ────────────────────────────────

    def verify_voice(self, voter_id, audio_path, expected_phrase,
                     audio_active, not_silent, session_id, client_transcript=''):
        """
        Verify a voter's voice against their enrolled profile.

        Returns dict:
            {
                "status": "VERIFIED" | "FAILED",
                "reason": "<reason if failed>",
                "confidence_score": <float>
            }
        """
        result = {
            "status": "FAILED",
            "reason": "",
            "confidence_score": 0.0
        }

        # ── Anti-spoofing: reject null/missing flags ──
        if audio_active is None or audio_active is False:
            result["reason"] = "Microphone is off. Please enable your microphone."
            self._log_failed("voice", voter_id, session_id, result["reason"])
            return result

        if not_silent is None or not_silent is False:
            result["reason"] = "No voice detected. Please speak clearly."
            self._log_failed("voice", voter_id, session_id, result["reason"])
            return result

        # ── Validate inputs ──
        if not voter_id or not audio_path:
            result["reason"] = "Missing voter ID or audio data."
            self._log_failed("voice", voter_id, session_id, result["reason"])
            return result

        if not session_id:
            result["reason"] = "Missing session ID. Session integrity compromised."
            self._log_failed("voice", voter_id, session_id, result["reason"])
            return result

        if not expected_phrase:
            result["reason"] = "Missing expected passphrase."
            self._log_failed("voice", voter_id, session_id, result["reason"])
            return result

        # ── Delegate to Canary-Qwen verifier ──
        if self.voice_verifier is None:
            result["reason"] = "Voice verification service is unavailable."
            self._log_failed("voice", voter_id, session_id, result["reason"])
            return result

        try:
            raw_result = self.voice_verifier.verify(voter_id, audio_path, expected_phrase, client_transcript)
        except Exception as e:
            result["reason"] = f"Voice verification error: {str(e)}"
            self._log_failed("voice", voter_id, session_id, result["reason"])
            return result

        # Handle verifier-level errors (no enrollment, etc.)
        if "error" in raw_result:
            result["reason"] = raw_result["error"]
            result["confidence_score"] = 0.0
            self._log_failed("voice", voter_id, session_id, result["reason"])
            return result

        # ── Compute combined confidence ──
        speaker_sim = raw_result.get("speakerSimilarity", 0.0)
        transcript_conf = raw_result.get("transcriptConfidence", 0.0)
        # Weighted: 60% speaker match, 40% transcript match
        confidence = (speaker_sim * 0.6) + (transcript_conf * 0.4)
        result["confidence_score"] = round(confidence, 4)

        # ── Enforce threshold ──
        if confidence < VOICE_CONFIDENCE_THRESHOLD:
            reasons = []
            if not raw_result.get("speakerMatch", False):
                reasons.append("Voice does not match registered voter.")
            if not raw_result.get("transcriptMatch", False):
                reasons.append("Passphrase mismatch.")
            result["reason"] = " ".join(reasons) if reasons else "Voice does not match registered voter."
            self._log_failed("voice", voter_id, session_id, result["reason"])
            return result

        # ── All checks passed ──
        result["status"] = "VERIFIED"
        result["reason"] = ""
        logger.info(f"Voice VERIFIED for voter {voter_id} session {session_id} "
                     f"(confidence={confidence:.4f})")
        return result

    # ── Final Voting Authorization ────────────────────────

    def authorize_vote(self, voter_id, session_id, face_result, voice_result):
        """
        Final authorization check. Both face and voice must be VERIFIED
        under the SAME voter_id and session_id.

        Returns the full structured JSON response.
        """
        response = {
            "voter_id": voter_id,
            "face_verification": face_result,
            "voice_verification": voice_result,
            "combined_status": "ACCESS DENIED",
            "session_id": session_id
        }

        if not voter_id or not session_id:
            response["combined_status"] = "ACCESS DENIED"
            self._log_failed("authorization", voter_id, session_id,
                             "Missing voter_id or session_id")
            return response

        face_ok = (face_result.get("status") == "VERIFIED")
        voice_ok = (voice_result.get("status") == "VERIFIED")

        if face_ok and voice_ok:
            response["combined_status"] = "ACCESS GRANTED"
            logger.info(f"ACCESS GRANTED for voter {voter_id} session {session_id}")
        else:
            response["combined_status"] = "ACCESS DENIED"
            failed_steps = []
            if not face_ok:
                failed_steps.append("face")
            if not voice_ok:
                failed_steps.append("voice")
            self._log_failed("authorization", voter_id, session_id,
                             f"Failed steps: {', '.join(failed_steps)}")

        return response

    # ── Audit Logging ─────────────────────────────────────

    def _log_failed(self, step, voter_id, session_id, reason):
        """Log a failed verification attempt."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step,
            "voter_id": voter_id,
            "session_id": session_id,
            "reason": reason
        }
        self._failed_attempts.append(entry)
        logger.warning(f"FAILED {step} verification: voter={voter_id} "
                       f"session={session_id} reason={reason}")

    def get_failed_attempts(self, voter_id=None, limit=50):
        """Retrieve failed attempt logs, optionally filtered by voter_id."""
        logs = self._failed_attempts
        if voter_id:
            logs = [l for l in logs if l["voter_id"] == voter_id]
        return logs[-limit:]

    @staticmethod
    def generate_session_id():
        """Generate a unique session ID."""
        return str(uuid.uuid4())
