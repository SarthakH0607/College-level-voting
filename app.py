"""
SmartVote Biometric Verification Microservice
Flask API for face and voice verification/enrollment
Secured with BiometricController for strict rule enforcement.
"""

import os
import json
import base64
import uuid
import tempfile
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

import sys
import os

# Add biometric-service folder to Python path so imports still work
sys.path.append(os.path.join(os.path.dirname(__file__), 'smartvote', 'biometric-service'))

# ── Configuration ────────────────────────────────────────
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'smartvote', 'biometric-service', 'data')
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, 'faces'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, 'voices'), exist_ok=True)

# Lazy-loaded modules (heavy imports)
_face_verifier = None
_voice_verifier = None
_controller = None


def get_face_verifier():
    global _face_verifier
    if _face_verifier is None:
        from face_verify import FaceVerifier
        _face_verifier = FaceVerifier(UPLOAD_DIR)
    return _face_verifier


def get_voice_verifier():
    global _voice_verifier
    if _voice_verifier is None:
        from voice_verify import VoiceVerifier
        _voice_verifier = VoiceVerifier(UPLOAD_DIR)
    return _voice_verifier


def get_controller():
    """Get the BiometricController singleton (lazy-loaded)."""
    global _controller
    if _controller is None:
        from biometric_controller import BiometricController
        _controller = BiometricController(
            face_verifier=get_face_verifier(),
            voice_verifier=get_voice_verifier()
        )
    return _controller


def _parse_bool_flag(value):
    """
    Parse a boolean flag from request data.
    Anti-spoofing: null/missing → treated as False (off).
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes')
    return bool(value)


# ── Endpoints ────────────────────────────────────────────

@app.route('/')
def serve_index():
    """Serve the main frontend page."""
    return send_from_directory(os.path.dirname(__file__), 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve all other HTML, CSS, and JS files from the root directory."""
    if os.path.exists(os.path.join(os.path.dirname(__file__), path)):
        return send_from_directory(os.path.dirname(__file__), path)
    return jsonify({"error": "File not found"}), 404

@app.route('/verify-face', methods=['POST'])
def verify_face():
    """Verify a face against enrolled profile via BiometricController.

    Expects JSON:
    {
        "image": "base64_jpeg",
        "uid": "voter_id",
        "camera_active": true|false,
        "face_detected": true|false,
        "session_id": "uuid"
    }

    Returns structured response per BiometricController spec.
    """
    data = request.get_json()
    if not data:
        return jsonify({
            "status": "FAILED",
            "reason": "Missing request body.",
            "similarity_score": 0.0
        }), 400

    voter_id = data.get('uid', '')
    image = data.get('image', '')
    camera_active = _parse_bool_flag(data.get('camera_active'))
    face_detected = _parse_bool_flag(data.get('face_detected'))
    session_id = data.get('session_id', '')

    try:
        controller = get_controller()
        result = controller.verify_face(
            voter_id=voter_id,
            image_b64=image,
            camera_active=camera_active,
            face_detected=face_detected,
            session_id=session_id
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Face verification error: {e}")
        return jsonify({
            "status": "FAILED",
            "reason": f"Internal error: {str(e)}",
            "similarity_score": 0.0
        }), 500


@app.route('/verify-voice', methods=['POST'])
def verify_voice():
    """Verify voice against enrolled profile via BiometricController.

    Expects multipart form:
        audio: file
        uid: voter_id
        expectedPhrase: string
        audio_active: "true"|"false"
        not_silent: "true"|"false"
        session_id: uuid

    Returns structured response per BiometricController spec.
    """
    uid = request.form.get('uid', '')
    expected_phrase = request.form.get('expectedPhrase', '')
    audio_active = _parse_bool_flag(request.form.get('audio_active'))
    not_silent = _parse_bool_flag(request.form.get('not_silent'))
    session_id = request.form.get('session_id', '')
    client_transcript = request.form.get('client_transcript', '')
    audio_file = request.files.get('audio')

    if not uid or not audio_file:
        return jsonify({
            "status": "FAILED",
            "reason": "Missing voter ID or audio file.",
            "confidence_score": 0.0
        }), 400

    try:
        # Save temp audio file
        temp_path = os.path.join(tempfile.gettempdir(), f'{uid}_verify.webm')
        audio_file.save(temp_path)

        controller = get_controller()
        result = controller.verify_voice(
            voter_id=uid,
            audio_path=temp_path,
            expected_phrase=expected_phrase,
            audio_active=audio_active,
            not_silent=not_silent,
            session_id=session_id,
            client_transcript=client_transcript
        )

        # Clean up temp file
        try:
            os.remove(temp_path)
        except OSError:
            pass

        return jsonify(result)
    except Exception as e:
        logger.error(f"Voice verification error: {e}")
        return jsonify({
            "status": "FAILED",
            "reason": f"Internal error: {str(e)}",
            "confidence_score": 0.0
        }), 500


@app.route('/verify-biometric', methods=['POST'])
def verify_biometric_combined():
    """Combined biometric verification endpoint.

    Accepts both face and voice verification in a single request.
    Returns the full structured authorization response.

    Expects JSON:
    {
        "voter_id": "uid",
        "session_id": "uuid",
        "face": {
            "image": "base64",
            "camera_active": true,
            "face_detected": true
        },
        "voice": {
            "audio_b64": "base64_audio",
            "audio_active": true,
            "not_silent": true,
            "expected_phrase": "..."
        }
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({
            "voter_id": "",
            "face_verification": {"status": "FAILED", "reason": "Missing request body.", "similarity_score": 0.0},
            "voice_verification": {"status": "FAILED", "reason": "Missing request body.", "confidence_score": 0.0},
            "combined_status": "ACCESS DENIED",
            "session_id": ""
        }), 400

    voter_id = data.get('voter_id', '')
    session_id = data.get('session_id', '')
    face_data = data.get('face', {})
    voice_data = data.get('voice', {})

    controller = get_controller()

    # ── Face verification ──
    face_result = controller.verify_face(
        voter_id=voter_id,
        image_b64=face_data.get('image', ''),
        camera_active=_parse_bool_flag(face_data.get('camera_active')),
        face_detected=_parse_bool_flag(face_data.get('face_detected')),
        session_id=session_id
    )

    # ── Voice verification ──
    # Decode base64 audio to temp file if provided
    voice_result = {"status": "FAILED", "reason": "No audio provided.", "confidence_score": 0.0}
    audio_b64 = voice_data.get('audio_b64', '')
    if audio_b64:
        try:
            audio_bytes = base64.b64decode(audio_b64)
            temp_path = os.path.join(tempfile.gettempdir(), f'{voter_id}_combined.webm')
            with open(temp_path, 'wb') as f:
                f.write(audio_bytes)

            voice_result = controller.verify_voice(
                voter_id=voter_id,
                audio_path=temp_path,
                expected_phrase=voice_data.get('expected_phrase', ''),
                audio_active=_parse_bool_flag(voice_data.get('audio_active')),
                not_silent=_parse_bool_flag(voice_data.get('not_silent')),
                session_id=session_id
            )

            try:
                os.remove(temp_path)
            except OSError:
                pass
        except Exception as e:
            voice_result = {
                "status": "FAILED",
                "reason": f"Audio processing error: {str(e)}",
                "confidence_score": 0.0
            }
    else:
        voice_result = controller.verify_voice(
            voter_id=voter_id,
            audio_path='',
            expected_phrase=voice_data.get('expected_phrase', ''),
            audio_active=_parse_bool_flag(voice_data.get('audio_active')),
            not_silent=_parse_bool_flag(voice_data.get('not_silent')),
            session_id=session_id
        )

    # ── Final authorization ──
    response = controller.authorize_vote(voter_id, session_id, face_result, voice_result)
    return jsonify(response)


@app.route('/failed-attempts', methods=['GET'])
def failed_attempts():
    """Get failed verification attempts (admin audit endpoint)."""
    voter_id = request.args.get('voter_id')
    limit = int(request.args.get('limit', 50))
    controller = get_controller()
    logs = controller.get_failed_attempts(voter_id=voter_id, limit=limit)
    return jsonify({'attempts': logs, 'count': len(logs)})


# ── Enrollment endpoints (unchanged, no controller needed) ──

@app.route('/enroll-face', methods=['POST'])
def enroll_face():
    """Enroll a face for a user.
    Expects JSON: { image: base64_jpeg, uid: string }
    Returns: { success: bool }
    """
    data = request.get_json()
    if not data or 'image' not in data or 'uid' not in data:
        return jsonify({'error': 'Missing image or uid'}), 400

    try:
        verifier = get_face_verifier()
        result = verifier.enroll(data['uid'], data['image'])
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/enroll-voice', methods=['POST'])
def enroll_voice():
    """Enroll a voice sample for a user.
    Expects multipart: audio file + uid
    Returns: { success: bool }
    """
    uid = request.form.get('uid')
    audio_file = request.files.get('audio')

    if not uid or not audio_file:
        return jsonify({'error': 'Missing uid or audio'}), 400

    try:
        temp_path = os.path.join(tempfile.gettempdir(), f'{uid}_enroll.webm')
        audio_file.save(temp_path)

        verifier = get_voice_verifier()
        result = verifier.enroll(uid, temp_path)

        os.remove(temp_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'SmartVote Biometric Service'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 4000))
    app.run(host='0.0.0.0', port=port, debug=True)
