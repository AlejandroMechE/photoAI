import os
import cv2
import numpy as np
import csv

class FuzzyFeatureExtractor:
    """
    Extracts numerical facial features suitable for Fuzzy Logic Systems (e.g. Scikit-Fuzzy or UPA library).
    Features computed:
    - MAR (Mouth Aspect Ratio): mouth height / mouth width
    - Mouth Curvature: lip corners vs lip center vertical delta (positive = smile, negative = frown)
    - Eyebrow Furrow Ratio: inner eyebrow separation / face width
    - Eyebrow Slant: tilt angle of inner to outer eyebrow
    - Eye Aspect Ratio (EAR): height/width of eyes
    """

    def __init__ (self):
        # Load OpenCV Haar cascade for fallback face & eye detection if needed
        self.face_cascade = None
        self.eye_cascade = None
        try:
            if hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data'):
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                eye_cascade_path = cv2.data.haarcascades + 'haarcascade_eye.xml'
                self.eye_cascade = cv2.CascadeClassifier(eye_cascade_path)
        except Exception as e:
            print(f"[Warning] Haar cascade initialization error: {e}")
        
        # Try importing MediaPipe for high-precision 468 landmark detection
        self.mp_face_mesh = None
        try:
            import mediapipe as mp
            self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5
            )
        except Exception as e:
            print(f"[Warning] MediaPipe FaceMesh not loaded ({e}). Using OpenCV geometric fallbacks.")

    def extract_features_from_image(self, image_path):
        """
        Reads an image file and returns a dictionary of fuzzy features [0.0 - 1.0 normalized range].
        """
        img = cv2.imread(image_path)
        if img is None:
            return None
        return self._process_img_matrix(img)

    def extract_features_from_image_bytes(self, image_bytes):
        """
        Decodes raw JPEG image bytes and returns fuzzy features dictionary.
        """
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        return self._process_img_matrix(img)

    def _process_img_matrix(self, img):
        h, w, c = img.shape
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        if self.mp_face_mesh:
            results = self.mp_face_mesh.process(rgb_img)
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0].landmark
                return self._extract_mediapipe_features(landmarks, w, h)

        # Fallback to OpenCV geometric features
        return self._extract_opencv_features(img)

    def _extract_mediapipe_features(self, landmarks, img_w, img_h):
        def p(idx):
            return np.array([landmarks[idx].x * img_w, landmarks[idx].y * img_h])

        # MediaPipe landmark indices
        # Upper lip top: 13, Lower lip bottom: 14
        # Mouth left corner: 61, Mouth right corner: 291
        top_lip = p(13)
        bottom_lip = p(14)
        left_corner = p(61)
        right_corner = p(291)

        mouth_width = np.linalg.norm(right_corner - left_corner) + 1e-6
        mouth_height = np.linalg.norm(bottom_lip - top_lip)
        mar = mouth_height / mouth_width

        # Mouth curvature: elevation of corners relative to mouth center
        lip_center_y = (top_lip[1] + bottom_lip[1]) / 2.0
        corners_avg_y = (left_corner[1] + right_corner[1]) / 2.0
        # Positive if corners are higher than center (smiling), negative if lower (sad/frown)
        mouth_curvature = (lip_center_y - corners_avg_y) / mouth_width

        # Eyebrows:
        # Left inner eyebrow: 55, Right inner eyebrow: 285
        # Left outer eyebrow: 70, Right outer eyebrow: 300
        left_inner_brow = p(55)
        right_inner_brow = p(285)
        left_outer_brow = p(70)
        right_outer_brow = p(300)

        inner_brow_dist = np.linalg.norm(right_inner_brow - left_inner_brow)
        eyebrow_furrow = inner_brow_dist / mouth_width

        # Eyebrow slant (angry: inner brows pull down -> inner brow Y > outer brow Y)
        brow_slant_left = (left_inner_brow[1] - left_outer_brow[1]) / mouth_width
        brow_slant_right = (right_inner_brow[1] - right_outer_brow[1]) / mouth_width
        eyebrow_slant = (brow_slant_left + brow_slant_right) / 2.0

        # Eye aspect ratio (EAR)
        # Left eye top: 159, bottom: 145, inner: 133, outer: 33
        left_eye_v = np.linalg.norm(p(159) - p(145))
        left_eye_h = np.linalg.norm(p(133) - p(33)) + 1e-6
        ear = left_eye_v / left_eye_h

        # Normalize features to clean 0.0 - 1.0 ranges for Fuzzy Logic input membership functions
        norm_mar = float(np.clip(mar * 2.0, 0.0, 1.0))
        norm_curvature = float(np.clip((mouth_curvature + 0.3) / 0.6, 0.0, 1.0)) # 0.5 is neutral
        norm_furrow = float(np.clip(eyebrow_furrow / 1.5, 0.0, 1.0))
        norm_slant = float(np.clip((eyebrow_slant + 0.2) / 0.4, 0.0, 1.0))
        norm_ear = float(np.clip(ear * 3.0, 0.0, 1.0))

        return {
            "mar": round(norm_mar, 4),
            "mouth_curvature": round(norm_curvature, 4),
            "eyebrow_furrow": round(norm_furrow, 4),
            "eyebrow_slant": round(norm_slant, 4),
            "ear": round(norm_ear, 4)
        }

    def _extract_opencv_features(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        if len(faces) == 0:
            return {
                "mar": 0.5,
                "mouth_curvature": 0.5,
                "eyebrow_furrow": 0.5,
                "eyebrow_slant": 0.5,
                "ear": 0.5
            }

        (x, y, w, h) = faces[0]
        # Approximate mouth area (lower third of face)
        mouth_roi = gray[y + int(h*0.65): y + h, x + int(w*0.2): x + int(w*0.8)]
        # Approximate brow area (upper third of face)
        brow_roi = gray[y + int(h*0.15): y + int(h*0.4), x + int(w*0.1): x + int(w*0.9)]

        mar_est = 0.4 if np.std(mouth_roi) < 30 else 0.7
        curvature_est = 0.5
        furrow_est = float(np.mean(brow_roi) / 255.0)

        return {
            "mar": round(mar_est, 4),
            "mouth_curvature": round(curvature_est, 4),
            "eyebrow_furrow": round(furrow_est, 4),
            "eyebrow_slant": 0.5,
            "ear": 0.5
        }

    def process_dataset_directory(self, dataset_dir, output_csv_path):
        """
        Scans dataset directory (subject/emotion/images) and writes dataset_fuzzy_features.csv
        """
        rows = []
        fieldnames = ["subject", "emotion", "filename", "mar", "mouth_curvature", "eyebrow_furrow", "eyebrow_slant", "ear"]

        if not os.path.exists(dataset_dir):
            return 0

        for subject in os.listdir(dataset_dir):
            subj_path = os.path.join(dataset_dir, subject)
            if not os.path.isdir(subj_path):
                continue

            for emotion in os.listdir(subj_path):
                emo_path = os.path.join(subj_path, emotion)
                if not os.path.isdir(emo_path):
                    continue

                for fname in os.listdir(emo_path):
                    if fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                        full_img_path = os.path.join(emo_path, fname)
                        feats = self.extract_features_from_image(full_img_path)
                        if feats:
                            row = {
                                "subject": subject,
                                "emotion": emotion,
                                "filename": fname,
                                **feats
                            }
                            rows.append(row)

        with open(output_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return len(rows)

if __name__ == '__main__':
    extractor = FuzzyFeatureExtractor()
    print("FuzzyFeatureExtractor initialized successfully.")
