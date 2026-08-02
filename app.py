import os
import re
import base64
import time
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from fuzzy_extractor import FuzzyFeatureExtractor
from cloud_store import CloudDatasetStore

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(BASE_DIR, 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

# Team roster and emotions
TEAM_MEMBERS = ['alan', 'alex', 'jorge', 'marco', 'francis', 'cristo']
EMOTIONS = ['feliz', 'enojado', 'triste']

# Initialize face detector & cloud store
face_cascade = None
try:
    if hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data'):
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
except Exception as e:
    print(f"[Warning] face_cascade init: {e}")

fuzzy_extractor = FuzzyFeatureExtractor()
cloud_store = CloudDatasetStore(BASE_DIR)

def crop_face(img, target_size=(224, 224)):
    """
    Detects face and crops with a 15% margin. If no face detected, returns resized center crop.
    """
    faces = []
    if face_cascade is not None and not face_cascade.empty():
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))
    
    if len(faces) > 0:
        faces = sorted(faces, key=lambda b: b[2] * b[3], reverse=True)
        (x, y, w, h) = faces[0]
        
        pad_x = int(w * 0.15)
        pad_y = int(h * 0.15)
        
        img_h, img_w = img.shape[:2]
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(img_w, x + w + pad_x)
        y2 = min(img_h, y + h + pad_y)
        
        cropped = img[y1:y2, x1:x2]
    else:
        h, w = img.shape[:2]
        min_dim = min(h, w)
        start_x = (w - min_dim) // 2
        start_y = (h - min_dim) // 2
        cropped = img[start_y:start_y+min_dim, start_x:start_x+min_dim]
        
    return cv2.resize(cropped, target_size)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify(cloud_store.get_stats())

@app.route('/api/upload', methods=['POST'])
def api_upload():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON payload"}), 400
        
    subject = data.get('subject', '').lower()
    emotion = data.get('emotion', '').lower()
    image_data = data.get('image', '')
    uploader = data.get('uploader', 'anonymous')
    
    if subject not in TEAM_MEMBERS:
        return jsonify({"error": f"Invalid subject: {subject}"}), 400
    if emotion not in EMOTIONS:
        return jsonify({"error": f"Invalid emotion: {emotion}"}), 400
    if not image_data:
        return jsonify({"error": "No image data received"}), 400
        
    try:
        image_bytes = base64.b64decode(re.sub('^data:image/.+;base64,', '', image_data))
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({"error": f"Failed to decode image: {str(e)}"}), 400

    # Auto crop face to 224x224
    cropped_img = crop_face(img, target_size=(224, 224))
    success, jpeg_encoded = cv2.imencode('.jpg', cropped_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    if not success:
        return jsonify({"error": "Failed to encode cropped image"}), 500
        
    jpeg_bytes = jpeg_encoded.tobytes()

    # Extract fuzzy features
    fuzzy_feats = fuzzy_extractor.extract_features_from_image_bytes(jpeg_bytes) if hasattr(fuzzy_extractor, 'extract_features_from_image_bytes') else {}

    # Upload to Cloud Storage & Manifest
    record = cloud_store.upload_image(subject, emotion, jpeg_bytes, fuzzy_features=fuzzy_feats, uploader=uploader)
    
    stats = cloud_store.get_stats()
    current_count = stats['stats'].get(subject, {}).get(emotion, 0)
    
    return jsonify({
        "success": True,
        "record": record,
        "subject": subject,
        "emotion": emotion,
        "current_count": current_count
    })

@app.route('/api/photos/<subject>/<emotion>', methods=['GET'])
def get_photos(subject, emotion):
    photos = cloud_store.get_photos_for_section(subject, emotion)
    return jsonify(photos)

@app.route('/dataset/<path:filename>')
def serve_dataset_file(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'dataset'), filename)

@app.route('/api/delete_photo', methods=['POST'])
def delete_photo():
    data = request.json
    subject = data.get('subject', '').lower()
    emotion = data.get('emotion', '').lower()
    filename = data.get('filename', '')
    
    deleted = cloud_store.delete_single_photo(subject, emotion, filename)
    if deleted:
        return jsonify({"success": True})
    return jsonify({"error": "Photo record not found"}), 404

@app.route('/api/clear_section', methods=['POST'])
def clear_section():
    data = request.json
    subject = data.get('subject', '').lower()
    emotion = data.get('emotion', '').lower()
    
    if subject not in TEAM_MEMBERS or emotion not in EMOTIONS:
        return jsonify({"error": "Invalid subject or emotion"}), 400
        
    count = cloud_store.clear_section(subject, emotion)
    return jsonify({"success": True, "deleted_count": count, "subject": subject, "emotion": emotion})

@app.route('/api/export_fuzzy_csv', methods=['GET'])
def export_fuzzy_csv():
    csv_path = os.path.join(EXPORT_DIR, 'dataset_fuzzy_features.csv')
    count = cloud_store.export_fuzzy_csv(csv_path)
    return send_file(csv_path, as_attachment=True, download_name='dataset_fuzzy_features.csv')

if __name__ == '__main__':
    print("Starting Cloud-Synchronized Face Dataset Studio on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
