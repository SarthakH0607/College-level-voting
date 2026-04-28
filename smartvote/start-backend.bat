@echo off
echo Starting SmartVote Biometric Service...
cd /d "%~dp0.."

echo Installing core requirements...
pip install flask flask-cors numpy opencv-python

echo Installing Face Recognition AI (DeepFace)...
pip install deepface tf-keras

echo.
echo Starting Flask App (Face AI = REAL, Voice = Stub Mode)
echo First launch will download the face model (~100MB). Please wait...
python app.py
pause
