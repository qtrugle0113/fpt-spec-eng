import type { components } from '../../lib/api.generated';

export type Schema = components['schemas'];
export type ETLItem = Extract<Schema['DefinitionPreview']['items'][number], { config: Schema['ETLConfig'] }>;
export const isETLItem = (item: Schema['DefinitionPreview']['items'][number]): item is ETLItem =>
  'config' in item && item.config !== undefined;
export type DagReview = { upload: Schema['DefinitionUpload']; preview: Schema['DefinitionPreview']; items: ETLItem[]; selected: string[]; ready: boolean };
export const failure = (error: unknown) => error instanceof Error ? error.message : 'The request could not be completed.';
