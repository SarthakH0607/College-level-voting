"""
Face Verification using DeepFace (ArcFace model)
Threshold: cosine similarity >= 0.45 (strict mode)
Pure Python — no C++ build tools required.
"""

import os
import base64
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
    print("DeepFace library loaded successfully.")
except ImportError:
    DEEPFACE_AVAILABLE = False
    print("WARNING: DeepFace not installed. Using stub mode.")


class FaceVerifier:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.faces_dir = os.path.join(data_dir, 'faces')
        os.makedirs(self.faces_dir, exist_ok=True)
        self.model_name = 'ArcFace'
        self.detector_backend = 'opencv'

    def _decode_image(self, base64_str):
        """Decode base64 image to numpy array."""
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        img_bytes = base64.b64decode(base64_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    def _save_image(self, image, path):
        """Save image to disk."""
        if CV2_AVAILABLE:
            cv2.imwrite(path, image)

    def enroll(self, uid, base64_image):
        """Store face image for a user."""
        try:
            img = self._decode_image(base64_image)
            if img is None:
                return {'success': False, 'error': 'Failed to decode image.'}

            # Save the face image for verification later
            img_path = os.path.join(self.faces_dir, f'{uid}.jpg')
            self._save_image(img, img_path)

            # Quick check: can we detect a face?
            if DEEPFACE_AVAILABLE:
                try:
                    DeepFace.represent(
                        img_path=img_path,
                        model_name=self.model_name,
                        detector_backend=self.detector_backend,
                        enforce_detection=False
                    )
                except Exception as e:
                    return {'success': False, 'error': f'No face detected: {str(e)}'}

            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def detect_face(self, base64_image):
        """
        Pre-check: detect whether a face exists in the image.
        Returns (face_detected: bool, embedding_or_none, error_msg).
        """
        try:
            img = self._decode_image(base64_image)
            if img is None:
                return False, None, "Failed to decode image."
        except Exception as e:
            return False, None, f"Image decode error: {str(e)}"

        if not DEEPFACE_AVAILABLE:
            return True, None, None

        try:
            # Save temp image for DeepFace
            temp_path = os.path.join(self.faces_dir, '_temp_detect.jpg')
            self._save_image(img, temp_path)
            result = DeepFace.represent(
                img_path=temp_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )
            os.remove(temp_path)
            if result and len(result) > 0:
                return True, result[0]['embedding'], None
            return False, None, "No face detected in the image."
        except Exception as e:
            return False, None, f"No face detected: {str(e)}"

    def verify(self, uid, base64_image):
        """
        Verify face against enrolled profile using DeepFace.
        Threshold: cosine distance. Lower = more similar.
        Returns: { verified: bool, confidence: float, error?: str }
        """
        img_path = os.path.join(self.faces_dir, f'{uid}.jpg')
        if not os.path.exists(img_path):
            return {'verified': False, 'confidence': 0.0, 'error': 'No face enrolled for this user.'}

        if not DEEPFACE_AVAILABLE:
            # Stub mode: return random low score (will fail threshold)
            return {'verified': False, 'confidence': 0.0, 'error': 'Face AI not available.'}

        try:
            # Save verification image to temp file
            verify_img = self._decode_image(base64_image)
            if verify_img is None:
                return {'verified': False, 'confidence': 0.0, 'error': 'Failed to decode image.'}

            # ANTI-SPOOFING: Check if a real face exists using Haar cascade
            gray = cv2.cvtColor(verify_img, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30))
            if len(faces) == 0:
                print(f"[FACE] uid={uid} REJECTED: No face detected by Haar cascade")
                return {'verified': False, 'confidence': 0.0, 'error': 'No face detected in the image.'}

            temp_path = os.path.join(self.faces_dir, f'{uid}_verify_temp.jpg')
            self._save_image(verify_img, temp_path)

            # DeepFace.verify compares two face images
            result = DeepFace.verify(
                img1_path=img_path,
                img2_path=temp_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )

            # Clean up temp
            try:
                os.remove(temp_path)
            except OSError:
                pass

            # DeepFace returns distance (lower = more similar)
            # Convert to similarity: 1 - distance
            distance = result.get('distance', 1.0)
            similarity = max(0.0, min(1.0, 1.0 - distance))
            verified = result.get('verified', False)

            print(f"[FACE] uid={uid} distance={distance:.4f} similarity={similarity:.4f} verified={verified}")

            return {
                'verified': verified,
                'confidence': round(similarity, 4)
            }
        except Exception as e:
            # Clean up temp on error
            temp_path = os.path.join(self.faces_dir, f'{uid}_verify_temp.jpg')
            try:
                os.remove(temp_path)
            except OSError:
                pass
            error_msg = str(e)
            if 'Face' in error_msg or 'face' in error_msg:
                return {'verified': False, 'confidence': 0.0, 'error': 'No face detected in the image.'}
            return {'verified': False, 'confidence': 0.0, 'error': error_msg}
