"""PostgreSQL create-only adapter."""
from . import common

def build_table(spec): return common.build_table(spec, 'postgresql')
def compile_table(spec): return common.compile_table(spec, 'postgresql')
def create(engine, spec): return common.create(engine, spec, 'postgresql')
