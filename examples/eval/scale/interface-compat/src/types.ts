export type HeaderMap = Record<string, string>;

export type RetryPredicate = (response: Response) => boolean;

export interface BackoffOptions {
  base: number;
  factor?: number;
  cap?: number;
  jitter?: boolean;
}

export interface RetryOptions {
  maxRetries?: number;
  backoff?: BackoffOptions;
  retryOn?: RetryPredicate;
  onRetry?: (attempt: number, error: unknown) => void;
}

export interface ClientOptions extends RetryOptions {
  baseUrl?: string;
  defaultHeaders?: HeaderMap;
  timeoutMs?: number;
}

export interface ResolvedRequest {
  url: string;
  headers: Record<string, string>;
  timeoutMs: number;
}

export const DEFAULT_MAX_RETRIES = 5;

export const DEFAULT_BACKOFF: Required<Omit<BackoffOptions, "cap">> & {
  cap?: number;
} = {
  base: 100,
  factor: 2,
  jitter: true,
};

export const DEFAULT_TIMEOUT_MS = 30_000;
