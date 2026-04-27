# SmartVote Biometric Microservice

Flask-based API for face and voice biometric verification with **strict anti-spoofing rules**.

## Architecture

```
┌─────────────────────────────────────────────┐
│  BiometricController (biometric_controller.py) │
│  ├─ verify_face()   → flag checks + threshold │
│  ├─ verify_voice()  → flag checks + threshold │
│  └─ authorize_vote() → combined authorization  │
├─────────────────────────────────────────────┤
│  FaceVerifier (face_verify.py)  │ InsightFace  │
│  VoiceVerifier (voice_verify.py)│ Canary-Qwen  │
└─────────────────────────────────────────────┘
```

## Security Rules

- **Face**: camera_active + face_detected + similarity ≥ 0.65
- **Voice**: audio_active + not_silent + confidence ≥ 0.75
- **Authorization**: Both VERIFIED + same voter_id + same session_id
- **Anti-spoofing**: null flags = off, no demo/stub bypass

## Setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Service
```bash
python app.py
```
Service starts at `http://localhost:5000`

### 3. Run Tests
```bash
python -m unittest test_controller -v
```

## API Endpoints

| Method | Endpoint | Response Format |
|--------|----------|----------------|
| POST | /verify-face | `{status, reason, similarity_score}` |
| POST | /verify-voice | `{status, reason, confidence_score}` |
| POST | /verify-biometric | Full combined authorization JSON |
| POST | /enroll-face | `{success: bool}` |
| POST | /enroll-voice | `{success: bool}` |
| GET | /failed-attempts | Audit log of failed attempts |
| GET | /health | `{status: "ok"}` |

## Response Format

```json
{
  "voter_id": "<id>",
  "face_verification": {
    "status": "VERIFIED | FAILED",
    "reason": "<reason if failed>",
    "similarity_score": 0.85
  },
  "voice_verification": {
    "status": "VERIFIED | FAILED",
    "reason": "<reason if failed>",
    "confidence_score": 0.82
  },
  "combined_status": "ACCESS GRANTED | ACCESS DENIED",
  "session_id": "<uuid>"
}
```
