export type DocumentId = string;

export type SortDirection = 'asc' | 'desc';

export interface ListParams {
  folderId: DocumentId;
  limit?: number;
  sort?: SortDirection;
}

export interface DocumentRecord {
  id: DocumentId;
  title: string;
  updatedAt: string;
}

export interface MoveParams {
  documentId: DocumentId;
  targetFolderId: DocumentId;
}
