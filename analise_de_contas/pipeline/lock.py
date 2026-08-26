"""Lock de execução do pipeline (fcntl)."""
import os
import fcntl


def acquire_pipeline_lock(output_dir):
    """Adquire lock exclusivo no diretório de saída (multiusuário)."""
    lock_path = output_dir / ".pipeline.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock_fd = open(lock_path, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(f"{os.getpid()}\n")
        lock_fd.flush()
        return lock_fd
    except (IOError, OSError):
        return None


def release_pipeline_lock(lock_fd):
    """Libera lock do pipeline."""
    if lock_fd:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
        except Exception:
            pass
