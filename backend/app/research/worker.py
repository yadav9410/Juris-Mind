"""Run with: python -m app.research.worker"""
import time
from app.db.session import SessionLocal
from app.research.job_service import claim_next_job, execute_job


def main(poll_seconds: float = 2.0):
    while True:
        with SessionLocal() as db:
            job = claim_next_job(db)
        if job:
            job_id = job.id
            execute_job(SessionLocal, job_id)
        else:
            time.sleep(poll_seconds)

if __name__ == "__main__":
    main()
