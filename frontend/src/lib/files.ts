import type { components } from './api.generated';
import { requestJSON } from './api';

export type SourceFile = components['schemas']['File'];
export type Parser = components['schemas']['ParserConfig'];
export type SourcePreview = components['schemas']['PreviewData'];
export type SourcePage = components['schemas']['FilePage'];
export const defaultParser: Parser = { encoding: 'utf-8', delimiter: ',', header_present: true, quote_character: '"', escape_character: null, null_representation: '\\N' };
export const normalizedParser = (value: Parser): Parser => ({ encoding: value.encoding.trim(), delimiter: value.delimiter,
  header_present: value.header_present, quote_character: value.quote_character, escape_character: value.escape_character || null,
  null_representation: value.null_representation });
export const parserSignature = (value: Parser) => JSON.stringify(normalizedParser(value));
export const listSourceFiles = async (offset: number, signal?: AbortSignal) =>
  (await requestJSON<SourcePage>(`/files?limit=20&offset=${offset}`, { signal })).data;
export const getSourceFile = (id: string, signal?: AbortSignal) => requestJSON<SourceFile>('/files/' + encodeURIComponent(id), { signal });
export async function uploadSourceFile(file: File, parser: Parser, signal?: AbortSignal) {
  const form = new FormData(); form.set('file', file); form.set('parser_json', JSON.stringify(normalizedParser(parser)));
  return requestJSON<SourceFile>('/files', { method: 'POST', form, signal });
}
export const previewSourceFile = async (id: string, parser: Parser, signal?: AbortSignal) => {
  const query = new URLSearchParams({ max_rows: '100', parser_json: JSON.stringify(normalizedParser(parser)) });
  return (await requestJSON<SourcePreview>(`/files/${encodeURIComponent(id)}/preview?${query}`, { signal })).data;
};
export const patchSourceParser = (id: string, etag: string, parser: Parser, signal?: AbortSignal) =>
  requestJSON<SourceFile>(`/files/${encodeURIComponent(id)}/parser`, { method: 'PATCH', body: normalizedParser(parser), etag, signal });
