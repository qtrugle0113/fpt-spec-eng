"""MySQL InnoDB consistent snapshot with an unbuffered SSCursor."""
from sqlalchemy import text
from .database import DatabaseSnapshotReader,SourceReadError


class SnapshotReader(DatabaseSnapshotReader):
    dialect='mysql'

    def prepare_session(self):
        self.connection.exec_driver_sql("SET SESSION time_zone = '+00:00'")
        self.connection.exec_driver_sql('SET SESSION MAX_EXECUTION_TIME = 120000')
        engine=self.connection.scalar(text('SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=:schema AND TABLE_NAME=:table'),
            {'schema':self.schema,'table':self.table_name})
        self.connection.rollback()
        if engine!='InnoDB':raise SourceReadError('MySQL source must be an InnoDB base table.')
        self.connection.exec_driver_sql('SET TRANSACTION READ ONLY')
        self.connection.exec_driver_sql('START TRANSACTION WITH CONSISTENT SNAPSHOT')
