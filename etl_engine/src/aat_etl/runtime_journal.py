"""Private bounded supervisor journal: identities only, never credentials or rows."""
import json
import os
from pathlib import Path
from .staging.quota import QuotaManager


class AttemptJournal:
    def __init__(self,path,binding_id,owner,*,terminal=False):
        self.path=Path(path)
        temporary=self.path.with_suffix('.part')
        if self.path.is_symlink() or self.path.exists() or temporary.is_symlink() or temporary.exists():
            raise ValueError('An unreconciled attempt journal already exists.')
        if type(terminal) is not bool:raise ValueError('Attempt terminal state must be boolean.')
        self.value=dict(binding_id=str(binding_id),owner=owner,pid=os.getpid(),attempts=[],
            exit_code=None,terminal=terminal)
        self.save()

    def save(self):
        _save(self.path,self.value)

    def reserve(self,run,attempt):
        identity=dict(run=str(run),attempt=str(attempt))
        if identity in self.value['attempts']:return
        if len(self.value['attempts'])>=4:raise ValueError('Unexpected staging allocation count.')
        self.value['attempts'].append(identity);self.save()


def _save(path,value):
    path=Path(path)
    if path.is_symlink():raise ValueError('Attempt journal cannot be a symlink.')
    temporary=path.with_suffix('.part')
    # Atomic replacement keeps the last complete journal after process death.
    with temporary.open('x',encoding='utf-8') as stream:
        os.chmod(temporary,0o600)
        json.dump(value,stream,separators=(',',':'));stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)
    descriptor=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


def record_exit(path,binding_id,exit_code):
    if type(exit_code) is not int or exit_code not in (0,20,21):
        raise ValueError('Invalid runtime child exit classification.')
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size>8192:
        return False
    value=json.loads(path.read_text(encoding='utf-8'))
    if value.get('binding_id')!=str(binding_id) or value.get('pid')!=os.getpid() \
            or not value.get('owner','').startswith(str(os.getpid())+':'):
        raise ValueError('Runtime child does not own its attempt journal.')
    value['exit_code']=exit_code
    _save(path,value)
    return True


class JournalQuota(QuotaManager):
    def __init__(self,engine,root,journal):
        super().__init__(engine,root);self.journal=journal

    def reserve(self,run,attempt,size):
        # Persist the allocation intent BEFORE its DB commit or filesystem write.
        # A killed child can leave a harmless intent without a reservation row.
        self.journal.reserve(run,attempt)
        return super().reserve(run,attempt,size)
