import os
import cv2
import numpy as np
from fuzzy_extractor import FuzzyFeatureExtractor

def test_pipeline():
    print("--- Running Pipeline Test ---")
    
    # 1. Create a dummy synthetic face image
    test_img = np.zeros((300, 300, 3), dtype=np.uint8)
    # Fill face circle (skin tone)
    cv2.circle(test_img, (150, 150), 100, (180, 200, 245), -1)
    # Eyes
    cv2.circle(test_img, (110, 120), 12, (255, 255, 255), -1)
    cv2.circle(test_img, (110, 120), 5, (0, 0, 0), -1)
    cv2.circle(test_img, (190, 120), 12, (255, 255, 255), -1)
    cv2.circle(test_img, (190, 120), 5, (0, 0, 0), -1)
    # Smile mouth (Feliz)
    cv2.ellipse(test_img, (150, 180), (40, 20), 0, 0, 180, (50, 50, 200), 4)

    test_dir = os.path.join("dataset", "test_user", "feliz")
    os.makedirs(test_dir, exist_ok=True)
    test_file = os.path.join(test_dir, "sample_smile_01.jpg")
    cv2.imwrite(test_file, test_img)
    print(f"Sample test face saved to: {test_file}")

    # 2. Extract features
    extractor = FuzzyFeatureExtractor()
    feats = extractor.extract_features_from_image(test_file)
    print("Extracted Fuzzy Features:", feats)

    # 3. Export CSV test
    export_csv = "test_fuzzy_export.csv"
    count = extractor.process_dataset_directory("dataset", export_csv)
    print(f"Exported {count} records to {export_csv}")
    assert os.path.exists(export_csv), "Export CSV should exist"
    print("--- Pipeline Test Successful! ---")

if __name__ == '__main__':
    test_pipeline()
