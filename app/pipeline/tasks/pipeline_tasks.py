"""
Celery tasks for pipeline execution.
"""
import os
import re
import subprocess
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from celery import current_task

from celery_app import celery_app
from pipeline.constants import BASE_DIR, CHECKPOINT_FILE, STATUS_FILE

logger = logging.getLogger("pipeline.tasks")


def _update_job_status(job_id: str, status: str, progress: dict | None = None, error: str | None = None):
    """Update job status in database."""
    # Import here to avoid circular imports
    from auth import get_db

    try:
        with get_db() as conn:
            update_fields = ["status = ?", "updated_at = ?"]
            params = [status, datetime.now(timezone.utc).isoformat()]

            if progress:
                update_fields.append("progress = ?")
                params.append(str(progress))

            if error:
                update_fields.append("error = ?")
                params.append(error)

            if status in ("completed", "failed"):
                update_fields.append("completed_at = ?")
                params.append(datetime.now(timezone.utc).isoformat())

            params.append(job_id)
            conn.execute(
                f"UPDATE pipeline_jobs SET {', '.join(update_fields)} WHERE id = ?",
                params,
            )
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")


def _get_job_output_dir(job_id: str) -> Path | None:
    """Get output directory for a job."""
    from auth import get_db

    try:
        with get_db() as conn:
            row = conn.execute("SELECT output_dir FROM pipeline_jobs WHERE id = ?", (job_id,)).fetchone()
            return Path(row["output_dir"]) if row and row["output_dir"] else None
    except Exception:
        return None


@celery_app.task(bind=True, name="pipeline.tasks.run_pipeline", max_retries=2, default_retry_delay=60)
def run_pipeline_task(self, job_id: str, pdf_path: str, domain: str, mode: str, force: bool, output_dir: str, user_id: int, notebooklm_profile: str):
    """
    Execute the full pipeline as a Celery task.

    Args:
        job_id: Unique job identifier
        pdf_path: Path to PDF file
        domain: Academic domain (cs, med, human)
        mode: Execution mode (full, lite)
        force: Force re-run from scratch
        output_dir: Output directory
        user_id: User ID who owns the job
        notebooklm_profile: NotebookLM profile to use
    """
    logger.info(f"Starting pipeline job {job_id}", extra={"job_id": job_id, "user_id": user_id})

    # Update status to running
    _update_job_status(job_id, "running", {"stage": "starting", "progress": 0})

    try:
        # Prepare environment
        env = os.environ.copy()
        env["NOTEBOOKLM_PROFILE"] = notebooklm_profile

        # Build command
        cmd = [
            sys.executable, "-m", "pipeline.runner",
            pdf_path,
            "--domain", domain,
            "--mode", mode,
            "--output-dir", output_dir,
        ]
        if force:
            cmd.append("--force")
        else:
            cmd.append("--resume")

        # Update progress
        _update_job_status(job_id, "running", {"stage": "executing", "progress": 10})

        # Run pipeline (runner é um módulo CLI: python -m pipeline.runner ...)
        proc = subprocess.run(cmd, env=env)
        if proc.returncode != 0:
            raise RuntimeError(f"Pipeline exited with code {proc.returncode}")

        # Mesma convenção de caminho do runner.main(): <output_dir>/peer_review_<safe_name>
        safe_name = re.sub(r"[^\w\-_]", "_", Path(pdf_path).stem)
        output_path = Path(output_dir) / f"peer_review_{safe_name}"
        if not output_path.exists():
            output_path = Path(output_dir)

        # Mark as completed
        _update_job_status(
            job_id,
            "completed",
            {"stage": "completed", "progress": 100, "output_dir": str(output_path)},
        )

        logger.info(f"Pipeline job {job_id} completed successfully", extra={"job_id": job_id})
        return {"status": "completed", "output_dir": str(output_path), "job_id": job_id}

    except Exception as exc:
        logger.exception(f"Pipeline job {job_id} failed", extra={"job_id": job_id})
        error_msg = str(exc)

        # Retry on transient errors
        if "rate limit" in error_msg.lower() or "timeout" in error_msg.lower():
            try:
                raise self.retry(exc=exc, countdown=60, max_retries=2)
            except self.MaxRetriesExceededError:
                pass

        _update_job_status(job_id, "failed", {"stage": "failed", "progress": 0}, error_msg)
        return {"status": "failed", "error": error_msg, "job_id": job_id}


@celery_app.task(name="pipeline.tasks.cleanup_old_jobs")
def cleanup_old_jobs():
    """Clean up old completed/failed jobs (older than 30 days)."""
    from auth import get_db
    from datetime import timedelta

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        with get_db() as conn:
            # Delete old job records
            result = conn.execute(
                "DELETE FROM pipeline_jobs WHERE created_at < ? AND status IN ('completed', 'failed')",
                (cutoff.isoformat(),),
            )
            logger.info(f"Cleaned up {result.rowcount} old pipeline jobs")
            return {"deleted": result.rowcount}
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"error": str(e)}


@celery_app.task(name="pipeline.tasks.get_job_status")
def get_job_status(job_id: str) -> dict:
    """Get job status from database."""
    from auth import get_db

    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, status, progress, error, output_dir, created_at, updated_at, completed_at "
                "FROM pipeline_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()

            if not row:
                return {"status": "not_found", "job_id": job_id}

            return dict(row)
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        return {"status": "error", "error": str(e), "job_id": job_id}