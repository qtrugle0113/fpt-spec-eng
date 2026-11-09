"""ETL immutable metadata; not an Airflow registry or ETL semantic validator."""
from uuid import UUID
from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, FetchedValue, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .definitions import Record
from .connections import immutable_guard
from .guards import safe_json_hash


class ETLDefinition(Record):
    __tablename__='etl_definitions'
    __table_args__=(UniqueConstraint('dag_id'),CheckConstraint("dag_id ~ '^[A-Za-z0-9_.-]{1,200}$'",name='ck_etl_dag'),
        CheckConstraint("owner='aat'",name='ck_etl_owner'),
        ForeignKeyConstraint(['id','current_revision_id'],['etl_definition_revisions.definition_id','etl_definition_revisions.id'],
                             name='fk_etl_current_revision',ondelete='RESTRICT',use_alter=True))
    dag_id: Mapped[str]=mapped_column(String(200))
    current_revision_id: Mapped[UUID | None]
    owner: Mapped[str]=mapped_column(String(16),default='aat',server_default='aat')
    lifecycle: Mapped[str]=mapped_column(String(32),default='DRAFT',server_default='DRAFT')


class ETLDefinitionRevision(Record):
    __tablename__='etl_definition_revisions'
    __table_args__=(UniqueConstraint('definition_id','revision'),UniqueConstraint('definition_id','id'),
        UniqueConstraint('definition_id','config_sha256'),CheckConstraint('revision>=1',name='ck_etl_revision'),
        CheckConstraint("config_sha256 ~ '^[0-9a-f]{64}$'",name='ck_etl_config_hash'))
    definition_id: Mapped[UUID]=mapped_column(ForeignKey('etl_definitions.id',ondelete='RESTRICT'))
    revision: Mapped[int]=mapped_column(Integer)
    upload_id: Mapped[UUID]=mapped_column(ForeignKey('definition_uploads.id',ondelete='RESTRICT'))
    config_json: Mapped[dict]=mapped_column(JSONB)
    config_sha256: Mapped[str]=mapped_column(String(64),server_default=FetchedValue())
    schema_fingerprint_source: Mapped[str | None]=mapped_column(String(64))
    schema_fingerprint_target: Mapped[str | None]=mapped_column(String(64))
    dependency_fingerprint: Mapped[str | None]=mapped_column(String(64))
    status: Mapped[str]=mapped_column(String(32),default='DRAFT',server_default='DRAFT')


class ColumnMapping(Record):
    __tablename__='column_mappings'
    __table_args__=(UniqueConstraint('etl_revision_id','ordinal'),
        Index('uq_mapping_enabled_target','etl_revision_id','target_column',unique=True,postgresql_where=text('enabled')),
        CheckConstraint('ordinal>=1',name='ck_mapping_ordinal'),CheckConstraint('length(btrim(target_column))>0',name='ck_mapping_target'),
        CheckConstraint("transformation IN ('DIRECT','CONSTANT','NULL_HANDLING','TYPE_CONVERSION')",name='ck_mapping_transform'),
        CheckConstraint("NOT enabled OR transformation='CONSTANT' OR source_column IS NOT NULL AND length(btrim(source_column))>0",name='ck_mapping_source'),
        CheckConstraint("NOT enabled OR transformation NOT IN ('CONSTANT','NULL_HANDLING') OR default_literal IS NOT NULL",name='ck_mapping_literal'),
        CheckConstraint("default_literal IS NULL OR jsonb_typeof(default_literal)='object' AND default_literal ?& ARRAY['logical_type','value'] AND default_literal-ARRAY['logical_type','value']='{}'::jsonb",name='ck_mapping_tagged_literal'))
    etl_revision_id: Mapped[UUID]=mapped_column(ForeignKey('etl_definition_revisions.id',ondelete='RESTRICT'))
    ordinal: Mapped[int]=mapped_column(Integer)
    source_column: Mapped[str | None]=mapped_column(String(255))
    target_column: Mapped[str]=mapped_column(String(255))
    transformation: Mapped[str]=mapped_column(String(32))
    default_literal: Mapped[dict | None]=mapped_column(JSONB(none_as_null=True))
    enabled: Mapped[bool]


safe_json_hash(ETLDefinitionRevision.__table__)
immutable_guard('etl_definition_revisions',('id','definition_id','revision','upload_id','config_json','config_sha256',
                 'schema_fingerprint_source','schema_fingerprint_target','dependency_fingerprint','created_at'))
immutable_guard('column_mappings',('id','etl_revision_id','ordinal','source_column','target_column','transformation','default_literal','enabled'))
