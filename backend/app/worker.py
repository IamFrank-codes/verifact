import time
from app.db import SessionLocal, Base, engine
from app.models import Verification
from app.services.verification import run_verification

def main():
    Base.metadata.create_all(bind=engine)
    while True:
        db = SessionLocal()
        try:
            queued = db.query(Verification).filter(Verification.status == 'queued').order_by(Verification.created_at).first()
            if queued:
                run_verification(db, queued.id)
            else:
                time.sleep(1)
        finally:
            db.close()
if __name__ == '__main__':
    main()
