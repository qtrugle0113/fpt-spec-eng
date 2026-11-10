"""Private bounded supervisor journal: identities only, never credentials or rows."""
import json
import os
from pathlib import Path
from .staging.quota import QuotaManager


class AttemptJournal:
    def __init__(self,path,binding_id,owner):
        self.path=Path(path)
        self.value=dict(binding_id=str(binding_id),owner=owner,pid=os.getpid(),attempts=[])
        self.save()

    def save(self):
        # The directory is created privately by the supervisor. Atomic replace
        # preserves the last complete journal if the child is killed mid-write.
        temporary=self.path.with_suffix('.part')
        with temporary.open('x',encoding='utf-8') as stream:
            os.chmod(temporary,0o600)
            json.dump(self.value,stream,separators=(',',':'));stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,self.path)
        descriptor=os.open(self.path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)

    def reserve(self,run,attempt):
        identity=dict(run=str(run),attempt=str(attempt))
        if identity in self.value['attempts']:return
        if len(self.value['attempts'])>=4:raise ValueError('Unexpected staging allocation count.')
        self.value['attempts'].append(identity);self.save()


class JournalQuota(QuotaManager):
    def __init__(self,engine,root,journal):
        super().__init__(engine,root);self.journal=journal

    def reserve(self,run,attempt,size):
        # Persist the allocation intent BEFORE its DB commit or filesystem write.
        # A killed child can leave a harmless intent without a reservation row.
        self.journal.reserve(run,attempt)
        return super().reserve(run,attempt,size)
