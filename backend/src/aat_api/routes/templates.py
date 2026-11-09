"""Download the repository's canonical schema 1.0 workbook artifacts."""
import hashlib
import os
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import Response
from aat_api.errors import APIError

router = APIRouter()


@router.get('/templates/table-definition', operation_id='get_templates_table_definition')
def table_definition():
    path = Path(os.environ.get('AAT_ASSETS_ROOT', '/opt/aat')) / 'templates' / 'Table Definition.xlsx'
    try: data = path.read_bytes()
    except OSError:
        raise APIError('TEMPLATE_UNAVAILABLE', 'Table definition template is unavailable.', 503) from None
    return Response(data, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': 'attachment; filename="Table Definition.xlsx"',
                             'ETag': '"' + hashlib.sha256(data).hexdigest() + '"',
                             'Cache-Control': 'no-cache'})
