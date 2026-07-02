"""
Script de migration : uploade les images locales existantes vers Supabase Storage.
Usage : python scripts/migrate_media_to_supabase.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.media_asset import MediaAsset
from app.services.storage_service import is_configured, upload_file as storage_upload


def migrate():
    if not is_configured():
        print("ERREUR : SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY doivent être définis.")
        sys.exit(1)

    db = SessionLocal()
    try:
        # Récupérer tous les médias avec URL locale (/uploads/...)
        local_medias = db.query(MediaAsset).filter(
            MediaAsset.url.like("/uploads/%")
        ).all()

        print(f"Found {len(local_medias)} local media files to migrate")

        migrated = 0
        failed = 0

        for media in local_medias:
            local_path = os.path.join(
                settings.UPLOAD_DIR,
                media.project_id,
                os.path.basename(media.url)
            )

            if not os.path.exists(local_path):
                print(f"  SKIP (file not found): {local_path}")
                failed += 1
                continue

            try:
                with open(local_path, "rb") as f:
                    content = f.read()

                new_url = storage_upload(
                    file_content=content,
                    filename=media.filename or os.path.basename(local_path),
                    project_id=media.project_id,
                    content_type=media.mime_type,
                )

                media.url = new_url
                db.commit()
                print(f"  OK: {os.path.basename(local_path)} -> {new_url}")
                migrated += 1

            except Exception as exc:
                print(f"  FAIL: {local_path} : {exc}")
                db.rollback()
                failed += 1

        print(f"\nMigration complete: {migrated} migrated, {failed} failed/skipped")

    finally:
        db.close()


if __name__ == "__main__":
    migrate()
