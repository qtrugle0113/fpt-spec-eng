"""MySQL 8.4 create-only adapter; DDL has an implicit commit boundary."""
from . import common

def build_table(spec): return common.build_table(spec, 'mysql')
def compile_table(spec): return common.compile_table(spec, 'mysql')
def create(engine, spec): return common.create(engine, spec, 'mysql')
