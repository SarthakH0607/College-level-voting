# SmartVote: College Level Election Platform 🗳️

A secure, biometric-verified digital voting system designed for college elections. SmartVote eliminates voter fraud using advanced facial recognition and voice passphrase verification, ensuring that every vote is cast by the true registered user.

## ✨ Features

- **Role-Based Dashboards:** Separate secure portals for Students, Teachers, and Admins.
- **Biometric Security:** 
  - **Face Verification:** Uses DeepFace (ArcFace model) for high-accuracy facial matching with anti-spoofing Haar Cascade pre-checks.
  - **Voice Verification:** Uses the Web Speech API to validate spoken passphrases in real-time, coupled with audio energy detection to prevent silent bypasses.
- **Live Real-time Dashboard:** Admins can watch vote counts update live as they happen.
- **Audit Trails:** The system logs all failed biometric attempts to prevent unauthorized access.

## 🛠️ Technology Stack

- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Backend:** Python, Flask
- **Database & Auth:** Firebase Firestore, Firebase Authentication
- **AI / Biometrics:** DeepFace (TensorFlow/Keras), OpenCV, Web Speech API

## 🚀 How to Run Locally

### 1. Start the AI Backend
1. Make sure Python is installed.
2. Double-click the `start-backend.bat` file.
3. It will install the required AI models (DeepFace, OpenCV, Flask) and start the server on `http://127.0.0.1:5000`.

### 2. Start the Frontend
1. Open the `index.html` file in your browser (or use a local server like Live Server).
2. Create an account, set up your biometrics in the Profile section, and start voting!

---
*Created as a College Mini-Project.*
