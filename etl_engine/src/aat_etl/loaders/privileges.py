"""Conservative recognition of exact MySQL SHOW GRANTS table/database scopes."""
import re


def mysql_permissions(grants,schema,table):
    allowed=set()
    for grant in grants:
        match=re.match(r'GRANT (.+) ON (.+) TO ',grant)
        if match is None:continue
        privileges,scope=match.groups()
        # MySQL database grants escape '_' to distinguish a literal database
        # name from a wildcard pattern. Accept only exact or global scopes;
        # do not infer access from arbitrary wildcard/role expressions.
        scope=scope.replace('`','').replace('\\_','_')
        if scope not in ('*.*',schema+'.*',schema+'.'+table):continue
        if privileges=='ALL PRIVILEGES':allowed.update(('SELECT','INSERT','UPDATE','DELETE','TRIGGER','CREATE','CREATE TEMPORARY TABLES'))
        else:allowed.update(privileges.split(', '))
    return allowed
