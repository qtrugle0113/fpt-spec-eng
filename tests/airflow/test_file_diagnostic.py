"""Diagnostic-only selector: do not treat an instrumented run as acceptance."""
__test__=False
from tests.airflow.test_execution import WorkflowFixture
from tests.airflow.test_file_database import FileDatabaseTests as _FileTests

class FileDiagnosticTests(WorkflowFixture):
    # Reproduce the prior terminal failure before a headerless route.
    def test_01_terminal_failure(self):
        self.workflow(extension='csv',strategy='FULL_REFRESH',file_data=b'id,note\ninvalid,first\n2,tail\n',expect_failure=True)

    def test_02_txt(self):
        self.workflow(target_kind='MYSQL',extension='txt',file_data=b'1|"\\N"\n2|\\N\n3|"line one\nline two"\n',
            parser_options={'header_present':False},expected_records=[(1,'\\N'),(2,None),(3,'line one\nline two')],fault_mode='file-diagnostic')


class FullSequenceDiagnosticTests(_FileTests):
    def file_route(self,extension,target_kind,strategy='APPEND'):
        if extension!='txt':return super().file_route(extension,target_kind,strategy=strategy)
        return self.workflow(target_kind=target_kind,extension='txt',strategy=strategy,
            file_data=b'1|"\\N"\n2|\\N\n3|"line one\nline two"\n',
            parser_options={'header_present':False},expected_records=[(1,'\\N'),(2,None),(3,'line one\nline two')],
            fault_mode='file-diagnostic')
