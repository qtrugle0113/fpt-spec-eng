"""Lock current metadata pins before authority or deployment publication."""
from uuid import UUID
from sqlalchemy import select
from aat_metadata.models.connections import Connection, ConnectionRevision
from aat_api.errors import APIError


def lock_current(session, config):
    revisions = [config['target']['connection_revision_id']]
    if config['source']['type'] == 'DB':
        revisions.append(config['source']['connection_revision_id'])
    for identity in sorted(set(revisions)):
        revision = session.get(ConnectionRevision, UUID(identity))
        parent = session.scalar(select(Connection).where(Connection.id==revision.connection_id).with_for_update())
        if parent.deleted_at is not None or parent.current_revision_id != revision.id or revision.test_status != 'SUCCESS':
            raise APIError('DEPENDENCY_CHANGED','A referenced connection changed. Preview again.',409)
    if config['source']['type'] != 'DB':
        from aat_api.services import files
        source = config['source']
        uploaded = files.require(session, UUID(source['file_id']), True)
        if (files.expired(uploaded) or uploaded.validation_status != 'VALID'
                or uploaded.sha256 != source['file_sha256'] or uploaded.parser_revision != source['parser_revision']):
            raise APIError('DEPENDENCY_CHANGED','The source file changed. Preview again.',409)
