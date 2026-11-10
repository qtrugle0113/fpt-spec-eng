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
    return download('Table Definition.xlsx')


@router.get('/templates/etl-definition', operation_id='get_templates_etl_definition')
def etl_definition():
    return download('ETL Definition.xlsx')


def download(filename):
    path = Path(os.environ.get('AAT_ASSETS_ROOT', '/opt/aat')) / 'templates' / filename
    try: data = path.read_bytes()
    except OSError:
        raise APIError('TEMPLATE_UNAVAILABLE', 'Definition template is unavailable.', 503) from None
    return Response(data, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': 'attachment; filename="' + filename + '"',
                             'ETag': '"' + hashlib.sha256(data).hexdigest() + '"',
                             'Cache-Control': 'no-cache'})
