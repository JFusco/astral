"""Cooperative paper-account ownership for one OS user on one host."""
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat

from .config import PAPER_URL

LOCK_DIRECTORY = Path.home() / ".astral-paper-executors"


class OwnershipError(Exception):
    pass


def account_identity(account):
    value = account.get("id") if isinstance(account, dict) else None
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise OwnershipError("Verified paper account identity is unavailable")
    return value


def private_owned(info, *, directory=False):
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise OwnershipError("Paper account lock storage must be private and owned by this user")
    if not directory and info.st_nlink != 1:
        raise OwnershipError("Paper account lock storage has an unsafe link")


class AccountLease:
    def __init__(self):
        self.identity = None
        self.pid = os.getpid()
        self.fd = self.directory_fd = None
        self.path = self.filename = None

    def check_process(self):
        if self.pid != os.getpid():
            raise OwnershipError("Inherited broker ownership is unavailable; open a new adapter")

    def acquire(self, identity):
        self.check_process()
        if self.identity is not None and self.identity != identity:
            raise OwnershipError("Paper account identity changed; reconcile before reopening")
        try:
            if self.fd is None:
                self.path = LOCK_DIRECTORY
                self.path.mkdir(mode=0o700, exist_ok=True)
                self.directory_fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
                private_owned(os.fstat(self.directory_fd), directory=True)
                self.filename = hashlib.sha256((PAPER_URL + "\0" + identity).encode()).hexdigest() + ".lock"
                self.fd = os.open(self.filename, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                                  0o600, dir_fd=self.directory_fd)
                private_owned(os.fstat(self.fd))
                try:
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise OwnershipError("Another local executor owns this paper account") from exc
                self.identity = identity
            self.check_storage()
        except (OSError, OwnershipError) as exc:
            self.close()
            if isinstance(exc, OwnershipError):
                raise
            raise OwnershipError("Paper account lock storage is unavailable") from exc

    def check_storage(self):
        directory = os.fstat(self.directory_fd)
        visible_directory = self.path.lstat()
        private_owned(directory, directory=True)
        private_owned(visible_directory, directory=True)
        held = os.fstat(self.fd)
        visible = os.stat(self.filename, dir_fd=self.directory_fd, follow_symlinks=False)
        private_owned(held)
        private_owned(visible)
        if ((directory.st_dev, directory.st_ino) != (visible_directory.st_dev, visible_directory.st_ino)
                or (held.st_dev, held.st_ino) != (visible.st_dev, visible.st_ino)):
            raise OwnershipError("Paper account lock storage changed; write blocked")

    def close(self):
        # Closing releases flock. Never unlink the name: another process may be
        # waiting on the same inode. An inherited child must not unlock its parent.
        for name in ("fd", "directory_fd"):
            descriptor = getattr(self, name)
            if descriptor is not None:
                os.close(descriptor)
                setattr(self, name, None)
