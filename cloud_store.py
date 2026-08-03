import os
import json
import time
import csv
import re
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

class CloudDatasetStore:
    """
    Hybrid Cloud Storage & Manifest Database Manager.
    Supports Cloudinary online storage with automatic local disk fallback.
    Maintains a real-time global manifest of images, subjects, emotions, and fuzzy feature matrices.
    """

    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.local_dataset_dir = os.path.join(self.base_dir, 'dataset')
        self.manifest_file = os.path.join(self.base_dir, 'cloud_manifest.json')
        os.makedirs(self.local_dataset_dir, exist_ok=True)

        self.team_members = ['alan', 'alex', 'jorge', 'marco', 'francis', 'cristo']
        self.emotions = ['feliz', 'enojado', 'triste']

        self.cloud_active = False
        self.cloudinary = None
        self._init_cloudinary()

        self.manifest = self._load_manifest()

    def _init_cloudinary(self):
        def clean_val(val):
            if not val:
                return ""
            val = val.strip()
            if val.startswith('<') and val.endswith('>'):
                val = val[1:-1].strip()
            return val

        cloudinary_url = clean_val(os.getenv('CLOUDINARY_URL'))
        cloud_name = clean_val(os.getenv('CLOUDINARY_CLOUD_NAME'))
        api_key = clean_val(os.getenv('CLOUDINARY_API_KEY'))
        api_secret = clean_val(os.getenv('CLOUDINARY_API_SECRET'))

        if (cloudinary_url and 'cloudinary://' in cloudinary_url) or (cloud_name and api_key and api_secret):
            try:
                import cloudinary
                import cloudinary.uploader
                import cloudinary.api
                
                if cloudinary_url and 'cloudinary://' in cloudinary_url:
                    # Clean any angle brackets inside CLOUDINARY_URL string
                    cloudinary_url = cloudinary_url.replace('<', '').replace('>', '')
                    cloudinary.config(cloudinary_url=cloudinary_url, secure=True)
                else:
                    cloudinary.config(
                        cloud_name=cloud_name,
                        api_key=api_key,
                        api_secret=api_secret,
                        secure=True
                    )
                self.cloudinary = cloudinary
                self.cloud_active = True
                print("[CloudDatasetStore] Successfully connected to Cloudinary storage.")
            except Exception as e:
                print(f"[CloudDatasetStore Warning] Could not initialize Cloudinary ({e}). Using Local Mode.")

    def _load_manifest(self):
        if os.path.exists(self.manifest_file):
            try:
                with open(self.manifest_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[CloudDatasetStore] Error reading manifest file ({e}). Initializing empty manifest.")
        return {"records": []}

    def _save_manifest(self):
        try:
            with open(self.manifest_file, 'w', encoding='utf-8') as f:
                json.dump(self.manifest, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[CloudDatasetStore] Error saving manifest file ({e}).")

    def is_cloud_active(self):
        return self.cloud_active

    def sync_from_cloud(self):
        """
        Queries Cloudinary Admin API to retrieve ALL images uploaded by all teammates,
        parsing subject, emotion, URL, and fuzzy metadata.
        """
        if not self.cloud_active or not self.cloudinary:
            return

        now = time.time()
        # Cache cloud sync for 3 seconds to keep UI fast
        if hasattr(self, '_last_sync_time') and (now - self._last_sync_time) < 3.0:
            return

        self._last_sync_time = now
        try:
            # Query all uploaded resources under prefix 'face_dataset_studio'
            resources = []
            next_cursor = None
            
            while True:
                kwargs = {
                    'type': 'upload',
                    'prefix': 'face_dataset_studio',
                    'max_results': 500,
                    'context': True,
                    'tags': True
                }
                if next_cursor:
                    kwargs['next_cursor'] = next_cursor

                result = self.cloudinary.api.resources(**kwargs)
                fetched = result.get('resources', [])
                resources.extend(fetched)
                next_cursor = result.get('next_cursor')
                if not next_cursor or len(resources) >= 2000:
                    break

            cloud_records_by_id = {}
            for res in resources:
                pub_id = res.get('public_id', '')
                parts = pub_id.split('/')
                if len(parts) >= 4 and parts[0] == 'face_dataset_studio':
                    subj = parts[1].lower()
                    emo = parts[2].lower()
                    raw_name = parts[3]
                    filename = f"{raw_name}.jpg"
                    
                    # Extract timestamp
                    ts_match = re.search(r'_(\d{10,13})$', raw_name)
                    timestamp_ms = int(ts_match.group(1)) if ts_match else int(time.time() * 1000)

                    # Extract fuzzy features from Cloudinary context metadata if present
                    ctx = res.get('context', {}).get('custom', {}) if isinstance(res.get('context'), dict) else {}
                    fuzzy_feats = {
                        "mar": float(ctx.get('mar', 0.5)),
                        "mouth_curvature": float(ctx.get('mouth_curvature', 0.5)),
                        "eyebrow_furrow": float(ctx.get('eyebrow_furrow', 0.5)),
                        "eyebrow_slant": float(ctx.get('eyebrow_slant', 0.5)),
                        "ear": float(ctx.get('ear', 0.5))
                    }

                    rec_id = f"{subj}_{emo}_{timestamp_ms}"
                    cloud_records_by_id[rec_id] = {
                        "id": rec_id,
                        "filename": filename,
                        "subject": subj,
                        "emotion": emo,
                        "url": res.get('secure_url', ''),
                        "public_id": pub_id,
                        "timestamp": timestamp_ms,
                        "uploader": ctx.get('uploader', 'teammate'),
                        "fuzzy_features": fuzzy_feats
                    }

            if cloud_records_by_id:
                # Merge cloud records with local manifest
                existing_map = {r.get('id'): r for r in self.manifest.get('records', [])}
                for rec_id, cloud_rec in cloud_records_by_id.items():
                    existing_map[rec_id] = cloud_rec

                # Sort by timestamp descending
                merged = list(existing_map.values())
                merged.sort(key=lambda r: r.get('timestamp', 0), reverse=True)
                self.manifest['records'] = merged
                self._save_manifest()
                print(f"[CloudDatasetStore Sync] Successfully synced {len(cloud_records_by_id)} global photos from Cloudinary.")

        except Exception as e:
            print(f"[CloudDatasetStore Sync Warning] Could not sync from Cloudinary ({e}).")

    def upload_image(self, subject, emotion, image_bytes, fuzzy_features=None, uploader="anonymous"):
        """
        Uploads image to Cloudinary (or saves to local disk), updates manifest database.
        """
        subject = subject.lower()
        emotion = emotion.lower()
        timestamp_ms = int(time.time() * 1000)
        filename = f"{subject}_{emotion}_{timestamp_ms}.jpg"

        url = ""
        public_id = ""

        fuzzy_features = fuzzy_features or {}
        context_dict = {
            "mar": str(fuzzy_features.get('mar', 0.5)),
            "mouth_curvature": str(fuzzy_features.get('mouth_curvature', 0.5)),
            "eyebrow_furrow": str(fuzzy_features.get('eyebrow_furrow', 0.5)),
            "eyebrow_slant": str(fuzzy_features.get('eyebrow_slant', 0.5)),
            "ear": str(fuzzy_features.get('ear', 0.5)),
            "uploader": str(uploader)
        }

        if self.cloud_active and self.cloudinary:
            try:
                folder_path = f"face_dataset_studio/{subject}/{emotion}"
                response = self.cloudinary.uploader.upload(
                    image_bytes,
                    folder=folder_path,
                    public_id=f"{subject}_{emotion}_{timestamp_ms}",
                    tags=[subject, emotion, "face_dataset_studio"],
                    context=context_dict
                )
                url = response.get('secure_url', '')
                public_id = response.get('public_id', '')
            except Exception as e:
                print(f"[CloudDatasetStore Error] Cloudinary upload failed ({e}). Falling back to local disk.")
                url, public_id = self._save_local_file(subject, emotion, filename, image_bytes)
        else:
            url, public_id = self._save_local_file(subject, emotion, filename, image_bytes)

        record = {
            "id": f"{subject}_{emotion}_{timestamp_ms}",
            "filename": filename,
            "subject": subject,
            "emotion": emotion,
            "url": url,
            "public_id": public_id,
            "timestamp": timestamp_ms,
            "uploader": uploader,
            "fuzzy_features": fuzzy_features
        }

        self.manifest["records"].append(record)
        self._save_manifest()
        return record

    def get_stats(self):
        """
        Returns global progress stats per team member and emotion.
        """
        self.sync_from_cloud()
        stats = {m: {e: 0 for e in self.emotions} for m in self.team_members}
        total_images = 0

        # Count from manifest database
        for rec in self.manifest.get("records", []):
            subj = rec.get("subject", "")
            emo = rec.get("emotion", "")
            if subj in stats and emo in stats[subj]:
                stats[subj][emo] += 1
                total_images += 1

        target_total = len(self.team_members) * len(self.emotions) * 100

        return {
            "team": self.team_members,
            "emotions": self.emotions,
            "stats": stats,
            "total_images": total_images,
            "target_total": target_total,
            "cloud_active": self.cloud_active
        }

    def get_photos_for_section(self, subject, emotion):
        self.sync_from_cloud()
        subject = subject.lower()
        emotion = emotion.lower()

        records = [
            rec for rec in self.manifest.get("records", [])
            if rec.get("subject") == subject and rec.get("emotion") == emotion
        ]
        records.sort(key=lambda r: r.get("timestamp", 0), reverse=True)
        return records

    def delete_single_photo(self, subject, emotion, photo_id_or_filename):
        subject = subject.lower()
        emotion = emotion.lower()

        new_records = []
        deleted = False

        for rec in self.manifest.get("records", []):
            if rec.get("subject") == subject and rec.get("emotion") == emotion and (rec.get("id") == photo_id_or_filename or rec.get("filename") == photo_id_or_filename):
                deleted = True
                pub_id = rec.get("public_id", "")
                if self.cloud_active and self.cloudinary and pub_id and not pub_id.startswith('/') and not os.path.exists(pub_id):
                    try:
                        self.cloudinary.uploader.destroy(pub_id)
                    except Exception as e:
                        print(f"[CloudDatasetStore] Cloud delete error: {e}")
                elif os.path.exists(pub_id):
                    try:
                        os.remove(pub_id)
                    except Exception as e:
                        print(f"[CloudDatasetStore] Local delete error: {e}")
            else:
                new_records.append(rec)

        if deleted:
            self.manifest["records"] = new_records
            self._save_manifest()

        return deleted

    def clear_section(self, subject, emotion):
        subject = subject.lower()
        emotion = emotion.lower()

        to_delete = [
            rec for rec in self.manifest.get("records", [])
            if rec.get("subject") == subject and rec.get("emotion") == emotion
        ]

        for rec in to_delete:
            pub_id = rec.get("public_id", "")
            if self.cloud_active and self.cloudinary and pub_id and not pub_id.startswith('/') and not os.path.exists(pub_id):
                try:
                    self.cloudinary.uploader.destroy(pub_id)
                except Exception as e:
                    print(f"[CloudDatasetStore] Cloud destroy error: {e}")
            elif os.path.exists(pub_id):
                try:
                    os.remove(pub_id)
                except Exception as e:
                    print(f"[CloudDatasetStore] Local remove error: {e}")

        # Remove from manifest
        self.manifest["records"] = [
            rec for rec in self.manifest.get("records", [])
            if not (rec.get("subject") == subject and rec.get("emotion") == emotion)
        ]
        self._save_manifest()
        return len(to_delete)

    def export_fuzzy_csv(self, csv_filepath):
        fieldnames = ["subject", "emotion", "filename", "url", "mar", "mouth_curvature", "eyebrow_furrow", "eyebrow_slant", "ear", "timestamp", "uploader"]
        rows = []

        for rec in self.manifest.get("records", []):
            feats = rec.get("fuzzy_features", {})
            row = {
                "subject": rec.get("subject", ""),
                "emotion": rec.get("emotion", ""),
                "filename": rec.get("filename", ""),
                "url": rec.get("url", ""),
                "mar": feats.get("mar", 0.5),
                "mouth_curvature": feats.get("mouth_curvature", 0.5),
                "eyebrow_furrow": feats.get("eyebrow_furrow", 0.5),
                "eyebrow_slant": feats.get("eyebrow_slant", 0.5),
                "ear": feats.get("ear", 0.5),
                "timestamp": rec.get("timestamp", 0),
                "uploader": rec.get("uploader", "anonymous")
            }
            rows.append(row)

        os.makedirs(os.path.dirname(csv_filepath), exist_ok=True)
        with open(csv_filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return len(rows)
