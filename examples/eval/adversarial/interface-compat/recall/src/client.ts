import { DocumentId, DocumentRecord, ListParams, MoveParams } from './types';

export interface ClientConfig {
  baseUrl: string;
  token: string;
}

export class DocsClient {
  private readonly baseUrl: string;
  private readonly token: string;

  constructor(config: ClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/+$/, '');
    this.token = config.token;
  }

  private async send<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        authorization: `Bearer ${this.token}`,
        ...(init?.headers ?? {}),
      },
    });
    if (!res.ok) {
      throw new Error(`request to ${path} failed: ${res.status}`);
    }
    return (await res.json()) as T;
  }

  async getDocument(id: DocumentId): Promise<DocumentRecord> {
    return this.send<DocumentRecord>(`/documents/${id}`);
  }

  async listDocuments(params: ListParams): Promise<DocumentRecord[]> {
    const query = new URLSearchParams();
    query.set('folder', String(params.folderId));
    if (params.limit != null) {
      query.set('limit', String(params.limit));
    }
    if (params.sort != null) {
      query.set('sort', params.sort);
    }
    return this.send<DocumentRecord[]>(`/documents?${query.toString()}`);
  }

  async moveDocument(params: MoveParams): Promise<DocumentRecord> {
    return this.send<DocumentRecord>(`/documents/${params.documentId}/move`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ folder: String(params.targetFolderId) }),
    });
  }
}
