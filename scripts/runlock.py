# -*- coding: utf-8 -*-
"""FLOKTRON · runlock.py — one FLOKTRON run at a time, safe on macOS, Linux and Windows.

The lock is an operating-system lock on data/.floktron.lock (fcntl.flock on macOS / Linux, msvcrt.locking on Windows):
  - taking it is one atomic step — two runs started in the same second cannot both get it;
  - the system frees it by itself when the process ends, even after a crash or a power cut — no stale lock, no
    "older than one hour" guess, and a long run (backup, weekly news) is never overtaken;
  - the file itself stays in place (deleting a lock file while another run waits on it would break the lock);
    it holds the PID and start time of the run that has it, for people reading data/run.log.

    with RunLock(path) as lock:
        if not lock.acquired:   # another FLOKTRON run is working
            ...
"""
import datetime
import os

try:
    import fcntl
except ImportError:          # Windows
    fcntl = None
    import msvcrt


class RunLock:
    def __init__(self, path):
        self.path = path
        self.acquired = False
        self._fd = None

    def acquire(self):
        """Try once, without waiting. True = this process has the lock."""
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if fcntl:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            os.close(fd)
            return False
        self._fd, self.acquired = fd, True
        try:  # who has it — for people only; the lock itself is the OS lock above
            os.lseek(fd, 0, os.SEEK_SET)
            os.ftruncate(fd, 0)
            os.write(fd, f"pid {os.getpid()} since {datetime.datetime.now():%Y-%m-%d %H:%M:%S}\n".encode())
        except OSError:
            pass
        return True

    def release(self):
        if self._fd is None:
            return
        try:
            if fcntl:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            else:
                os.lseek(self._fd, 0, os.SEEK_SET)
                msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        os.close(self._fd)
        self._fd, self.acquired = None, False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()
