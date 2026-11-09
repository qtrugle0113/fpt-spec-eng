"""PostgreSQL read-only REPEATABLE READ with a server-side cursor."""
from .database import DatabaseSnapshotReader


class SnapshotReader(DatabaseSnapshotReader):
    dialect='postgresql'

    def prepare_session(self):
        self.connection.exec_driver_sql('SET TRANSACTION READ ONLY')
        self.connection.exec_driver_sql('SET LOCAL statement_timeout = 120000')
        self.connection.exec_driver_sql("SET LOCAL TIME ZONE 'UTC'")
