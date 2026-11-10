"""Driver values preserve aware instants on UTC MySQL sessions."""
from datetime import datetime,timezone


def driver_row(values,columns,dialect):
    profiles={c['name']:c for c in columns}
    result=dict(values)
    if dialect=='mysql':
        for name,value in result.items():
            if isinstance(value,datetime) and value.utcoffset() is not None:
                if profiles[name].get('timezone_semantics')!='aware':raise ValueError('Aware datetime cannot be bound to a naive target.')
                result[name]=value.astimezone(timezone.utc).replace(tzinfo=None)
    return result
