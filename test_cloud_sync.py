import os
import cv2
import numpy as np
from cloud_store import CloudDatasetStore

def test_cloud_sync():
    print("--- Running Cloud Sync & Manifest Test ---")
    store = CloudDatasetStore()

    print(f"Cloud Storage Active: {store.is_cloud_active()}")

    # 1. Generate dummy face image bytes
    test_img = np.zeros((224, 224, 3), dtype=np.uint8)
    cv2.circle(test_img, (112, 112), 80, (200, 220, 250), -1)
    cv2.circle(test_img, (80, 90), 10, (0, 0, 0), -1)
    cv2.circle(test_img, (144, 90), 10, (0, 0, 0), -1)
    cv2.ellipse(test_img, (112, 140), (30, 15), 0, 0, 180, (0, 0, 255), 3)

    _, jpeg_buf = cv2.imencode('.jpg', test_img)
    jpeg_bytes = jpeg_buf.tobytes()

    # 2. Upload photo for Alan (feliz)
    dummy_feats = {"mar": 0.65, "mouth_curvature": 0.8, "eyebrow_furrow": 0.7, "eyebrow_slant": 0.5, "ear": 0.5}
    rec = store.upload_image("alan", "feliz", jpeg_bytes, fuzzy_features=dummy_feats, uploader="test_runner")
    print("Uploaded Record:", rec)

    # 3. Verify stats
    stats = store.get_stats()
    print("Global Team Stats:", stats['stats']['alan'])
    assert stats['stats']['alan']['feliz'] >= 1, "Alan's feliz count should be at least 1"

    # 4. Verify Export CSV
    export_path = os.path.join("exports", "test_master_dataset.csv")
    count = store.export_fuzzy_csv(export_path)
    print(f"Exported {count} global records to {export_path}")
    assert os.path.exists(export_path), "CSV file should exist"

    print("--- Cloud Sync Verification Test Passed Successfully! ---")

if __name__ == '__main__':
    test_cloud_sync()
