"""Confined Linux DAG writer; a returned file is durable, not yet deployed."""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Artifact:
    key: str
    sha256: str


def write(source: bytes, *, file_id: UUID | str, root: Path | None = None) -> Artifact:
    key = str(UUID(str(file_id))) + '.py'
    if not isinstance(source, bytes) or not source or len(source) > 2 * 1024 * 1024:
        raise ValueError('A bounded nonempty Python artifact is required.')
    directory = Path(root if root is not None else os.environ.get('AAT_DAGS_ROOT', '/data/generated_dags'))
    # Open each component without following symlinks, then keep the directory FD
    # pinned throughout write/rename/fsync to avoid path substitution races.
    absolute = directory.absolute()
    directory_fd = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in absolute.parts[1:]:
            if component in ('.', '..'):
                raise ValueError('A canonical DAG directory is required.')
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = child
        try:
            existing = os.stat(key, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and not stat.S_ISREG(existing.st_mode):
            raise ValueError('The generated artifact must be a regular file.')
        temporary = '.' + uuid4().hex + '.tmp'
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o640, dir_fd=directory_fd)
        try:
            with os.fdopen(fd, 'wb') as output:
                output.write(source)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, key, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
            os.fsync(directory_fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
    finally:
        os.close(directory_fd)
    return Artifact(key=key, sha256=hashlib.sha256(source).hexdigest())
