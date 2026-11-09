"""Sinh types TypeScript từ hợp đồng OpenAPI; không cần thêm dependency Node."""
import hashlib
import json
from pathlib import Path
import sys
import yaml


def typescript(schema):
    if '$ref' in schema:
        name=schema['$ref'].split('/')[-1].replace('~1','/').replace('~0','~')
        return 'components["schemas"]['+json.dumps(name)+']'
    if 'enum' in schema:return ' | '.join(json.dumps(value,ensure_ascii=True) for value in schema['enum'])
    for keyword,operator in [('anyOf',' | '),('oneOf',' | ')]:
        if keyword in schema:
            base={key:value for key,value in schema.items() if key!=keyword}
            variants=[]
            for value in schema[keyword]:
                variant={**base,**value}
                if 'properties' in base:
                    variant['properties']={**base['properties'],**value.get('properties',{})}
                    variant['required']=list(set(base.get('required',[]))|set(value.get('required',[])))
                variants.append(typescript(variant))
            return '('+operator.join(variants)+')'
    kind=schema.get('type')
    if isinstance(kind,list):return '('+' | '.join(typescript({**schema,'type':value}) for value in kind)+')'
    if kind=='string':return 'Blob' if schema.get('format')=='binary' else 'string'
    if kind in ('number','integer'):return 'number'
    if kind=='boolean':return 'boolean'
    if kind=='null':return 'null'
    if kind=='array':return 'Array<'+typescript(schema.get('items',{}))+'>'
    if kind=='object' or 'properties' in schema:
        required=set(schema.get('required',[]))
        forbidden=set(schema.get('not',{}).get('required',[]))
        fields=[json.dumps(key)+('' if key in required else '?')+': '+('never' if key in forbidden else typescript(value))+';'
                for key,value in schema.get('properties',{}).items()]
        extra=schema.get('additionalProperties',False)
        if extra is True:fields.append('[key: string]: unknown;')
        elif isinstance(extra,dict):fields.append('[key: string]: '+typescript(extra)+';')
        base='{ '+' '.join(fields)+' }' if fields else 'Record<string, never>'
        if 'allOf' in schema:
            unconditional=[value for value in schema['allOf'] if 'if' not in value]
            if unconditional:base+=' & '+' & '.join(typescript(value) for value in unconditional)
        return base
    if 'allOf' in schema:return '('+' & '.join(typescript(value) for value in schema['allOf'])+')'
    return 'unknown'


source=Path(sys.argv[1]);target=Path(sys.argv[2])
raw=source.read_bytes();document=yaml.safe_load(raw)
lines=['// Generated from canonical OpenAPI. Regenerate; do not edit manually.',
       '// Source SHA256: '+hashlib.sha256(raw).hexdigest(),'export interface components {','  schemas: {']
for name,schema in document['components']['schemas'].items():
    lines.append('    '+json.dumps(name)+': '+typescript(schema)+';')
lines+=['  };','}','export interface operations {']
for path,item in document['paths'].items():
    for method,operation in item.items():
        if method not in ('get','post','put','patch','delete','head','options','trace'):continue
        body=operation.get('requestBody',{}).get('content',{})
        request=next(iter(body.values())).get('schema',{}) if body else None
        responses=[]
        for status,response in operation['responses'].items():
            if status.startswith('2'):
                content=response.get('content',{})
                responses.append(typescript(next(iter(content.values()))['schema']) if content else 'undefined')
        lines.append('  '+json.dumps(operation['operationId'])+': { method: '+json.dumps(method.upper())+
                     '; path: '+json.dumps(path)+'; request: '+(typescript(request) if request else 'never')+
                     '; response: '+(' | '.join(dict.fromkeys(responses)) or 'never')+'; };')
lines+=['}','']
target.parent.mkdir(parents=True,exist_ok=True)
target.write_bytes('\n'.join(lines).encode('utf-8'))
