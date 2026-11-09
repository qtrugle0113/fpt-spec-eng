"""Freeze reviewed initial DDL into a static Alembic revision; never run on live DB."""
from pathlib import Path
from pprint import pformat
from sqlalchemy.schema import CreateTable,CreateIndex,AddConstraint
from sqlalchemy.dialects import postgresql
from aat_metadata.models.registry import Base

dialect=postgresql.dialect(paramstyle='named')
statements=[]
for ddl in Base.metadata.dispatch.before_create:
    statements.append(str(ddl.compile(dialect=dialect)))
for table in Base.metadata.sorted_tables:
    statements.append(str(CreateTable(table).compile(dialect=dialect)))
    for index in sorted(table.indexes,key=lambda i:i.name):statements.append(str(CreateIndex(index).compile(dialect=dialect)))
    for ddl in table.dispatch.after_create:statements.append(str(ddl.compile(dialect=dialect)))
for table in Base.metadata.sorted_tables:
    for constraint in sorted(table.foreign_key_constraints,key=lambda c:c.name or ''):
        if constraint.use_alter:statements.append(str(AddConstraint(constraint).compile(dialect=dialect)))
target=Path('/tmp/backend/alembic/versions/0001_metadata.py');target.parent.mkdir(parents=True,exist_ok=True)
target.write_text('"""Frozen initial app metadata DDL; no live model imports."""\nfrom alembic import op\nrevision="0001_metadata"\ndown_revision=None\nbranch_labels=None\ndepends_on=None\n\nSTATEMENTS='+pformat(tuple(statements),width=100)+'\n\ndef upgrade():\n    for statement in STATEMENTS:op.execute(statement)\n\ndef downgrade():\n    raise RuntimeError("Automatic metadata downgrade is unsupported; restore a verified backup")\n')
print('Frozen',len(statements),'DDL statements')
