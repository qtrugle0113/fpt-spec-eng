"""Strict bounded CSV/TXT lexer retaining quoted-token provenance."""
import codecs
from dataclasses import dataclass
import io
import sys
from pydantic import BaseModel,ConfigDict,Field,StrictBool,field_validator,model_validator

MAX_RECORD_BYTES=1024*1024
MAX_BUFFER_BYTES=8*1024*1024


class ParserConfig(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True,strict=True)
    encoding:str=Field(default='utf-8',min_length=1,max_length=64)
    delimiter:str=Field(min_length=1,max_length=1)
    header_present:StrictBool
    quote_character:str=Field(min_length=1,max_length=1)
    escape_character:str|None=Field(default=None,min_length=1,max_length=1)
    null_representation:str=Field(max_length=255)

    @field_validator('encoding')
    @classmethod
    def text_encoding(cls,value):
        try:
            codec=codecs.lookup(value)
            decoder=codecs.getincrementaldecoder(codec.name)(errors='strict')
            if not isinstance(decoder.decode(b''),str):raise ValueError()
            return codec.name
        except (LookupError,TypeError,ValueError):raise ValueError('A supported text encoding is required.') from None

    @model_validator(mode='after')
    def grammar(self):
        for value in (self.delimiter,self.quote_character,self.escape_character):
            if value is not None and value in ('\r','\n','\0'):raise ValueError('Parser grammar characters cannot be line endings or NUL.')
        if self.delimiter==self.quote_character:raise ValueError('Delimiter and quote character must differ.')
        if self.escape_character==self.delimiter:raise ValueError('Escape character must differ from the delimiter.')
        try:
            for value in (self.delimiter,self.quote_character,self.escape_character,self.null_representation):
                if value is not None:value.encode('utf-8')
        except UnicodeError:raise ValueError('Parser fields must contain valid Unicode text.') from None
        if '\0' in self.null_representation:raise ValueError('NULL representation cannot contain NUL.')
        return self


class DelimitedError(ValueError):
    def __init__(self,code,message,*,line,record,column=None):
        self.code=code;self.line=line;self.record=record;self.column=column
        super().__init__(message)


@dataclass(frozen=True)
class Token:
    text:str
    was_quoted:bool


@dataclass(frozen=True)
class Record:
    columns:list[str]
    values:list[str|None]
    tokens:list[Token]
    line:int
    record:int


def _characters(source,encoding):
    decoder=codecs.getincrementaldecoder(encoding)(errors='strict')
    while chunk:=source.read(4096):
        # Count source bytes before decoding, including stateful encodings and
        # sequences that produce no character yet. Never read/materialize a row.
        for value in chunk:yield decoder.decode(bytes((value,))),1
    final=decoder.decode(b'',final=True)
    if final:yield final,0


def _lex(source,config):
    line=1;start_line=1;physical_record=0;raw_bytes=0;utf8_bytes=0
    state='START';quoted=False;escaped=False;skip_lf=False;previous_cr=False;first=True
    buffer=io.StringIO();tokens=[];token_bytes=0;saw_record=False
    def fail(code,message):
        raise DelimitedError(code,message,line=start_line,record=physical_record if config.header_present else physical_record+1,column=len(tokens)+1)
    def field():
        nonlocal buffer,quoted,token_bytes
        value=buffer.getvalue();buffer.close();buffer=io.StringIO()
        token=Token(value,quoted);tokens.append(token);quoted=False
        token_bytes+=sys.getsizeof(token)+sys.getsizeof(value)+16
        if token_bytes>MAX_BUFFER_BYTES:fail('ROW_BUFFER_LIMIT','Record exceeds the bounded parser buffer.')
    try:
        for fragment,count in _characters(source,config.encoding):
            raw_bytes+=count
            if raw_bytes>MAX_RECORD_BYTES:fail('RECORD_TOO_LARGE','Record exceeds 1 MiB.')
            for character in fragment:
                if first:
                    first=False
                    if character=='\ufeff' and config.header_present:continue
                if skip_lf:
                    skip_lf=False
                    if character=='\n':
                        raw_bytes=utf8_bytes=0;previous_cr=False
                        continue
                utf8_bytes+=len(character.encode('utf-8'))
                if utf8_bytes>MAX_RECORD_BYTES:fail('RECORD_TOO_LARGE','Decoded record exceeds 1 MiB.')
                if character=='\r':line+=1
                elif character=='\n' and not previous_cr:line+=1
                previous_cr=character=='\r'
                saw_record=True
                if escaped:
                    buffer.write(character);escaped=False
                    continue
                if state!='AFTER_QUOTE' and config.escape_character not in (None,config.quote_character) and character==config.escape_character:
                    escaped=True
                    if state=='START':state='UNQUOTED'
                    continue
                if state=='QUOTED':
                    if character==config.quote_character:state='AFTER_QUOTE'
                    else:buffer.write(character)
                    continue
                if state=='AFTER_QUOTE' and character==config.quote_character:
                    buffer.write(character);state='QUOTED'
                    continue
                if character==config.delimiter:
                    field();state='START'
                    continue
                if character in ('\r','\n'):
                    field()
                    yield tokens,start_line
                    physical_record+=1;tokens=[];token_bytes=0;state='START';saw_record=False
                    raw_bytes=utf8_bytes=0;start_line=line;skip_lf=character=='\r'
                    continue
                if state=='AFTER_QUOTE':fail('TRAILING_QUOTED_DATA','Unexpected data after a closing quote.')
                if character==config.quote_character:
                    if state!='START':fail('UNEXPECTED_QUOTE','Quote must begin at the start of a field.')
                    quoted=True;state='QUOTED'
                else:buffer.write(character);state='UNQUOTED'
        if escaped:fail('DANGLING_ESCAPE','File ends with an incomplete escape sequence.')
        if state=='QUOTED':fail('UNTERMINATED_QUOTE','File ends inside a quoted field.')
        if saw_record or tokens:
            field();yield tokens,start_line
    except UnicodeError:
        fail('INVALID_ENCODING','Source bytes do not match the selected text encoding.')
    finally:buffer.close()


class Reader:
    def __init__(self,source,config):
        self.config=config;self.lexer=_lex(source,config);self.record=0;self.pending=None
        first=next(self.lexer,None)
        if first is None:raise DelimitedError('EMPTY_FILE','The source file is empty.',line=1,record=0)
        tokens,line=first
        if config.header_present:
            self.columns=[token.text for token in tokens]
            if any(name=='' for name in self.columns) or len(set(self.columns))!=len(self.columns):
                raise DelimitedError('INVALID_HEADER','Header names must be nonempty and unique.',line=line,record=0)
        else:
            self.columns=['column_'+str(index) for index in range(1,len(tokens)+1)]
            self.pending=first

    def __iter__(self):return self

    def __next__(self):
        if self.pending is not None:tokens,line=self.pending;self.pending=None
        else:tokens,line=next(self.lexer)
        self.record+=1
        if len(tokens)!=len(self.columns):
            raise DelimitedError('FIELD_COUNT_MISMATCH','Record field count does not match the header.',line=line,record=self.record)
        values=[None if not token.was_quoted and token.text==self.config.null_representation else token.text for token in tokens]
        return Record(self.columns,values,tokens,line,self.record)

    def close(self):self.lexer.close()


def read(source,config):return Reader(source,config)


def preview(source,config,*,max_rows=100):
    if isinstance(max_rows,bool) or not isinstance(max_rows,int) or not 0<=max_rows<=100:raise ValueError('Preview accepts zero to 100 rows.')
    reader=Reader(source,config);rows=[];used=sum(sys.getsizeof(name) for name in reader.columns)
    limited=True
    try:
        for _ in range(max_rows):
            record=next(reader,None)
            if record is None:limited=False;break
            size=sys.getsizeof(record.values)+sum(sys.getsizeof(value) for value in record.values)
            if used+size>MAX_BUFFER_BYTES:break
            rows.append(record.values);used+=size
        return dict(columns=reader.columns,rows=rows,limited=limited)
    finally:reader.close()
