import {
  ClientOptions,
  DEFAULT_MAX_RETRIES,
  DEFAULT_TIMEOUT_MS,
  ResolvedRequest,
} from "./types";
import { mergeHeaders } from "./headers";
import { computeBackoff, parseRetryAfter } from "./backoff";
import { defaultRetryOn } from "./status";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function resolveRequest(
  input: string,
  init: RequestInit | undefined,
  options: ClientOptions,
): ResolvedRequest {
  const url = options.baseUrl ? new URL(input, options.baseUrl).toString() : input;
  const headers = mergeHeaders(
    options.defaultHeaders,
    (init?.headers as Record<string, string>) ?? undefined,
  );
  return {
    url,
    headers,
    timeoutMs: options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  };
}

export interface Client {
  fetch(input: string, init?: RequestInit): Promise<Response>;
}

export function createClient(options: ClientOptions = {}): Client {
  const maxRetries = options.maxRetries ?? DEFAULT_MAX_RETRIES;
  const retryOn = options.retryOn ?? defaultRetryOn;

  async function run(input: string, init?: RequestInit): Promise<Response> {
    const resolved = resolveRequest(input, init, options);
    let lastError: unknown;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), resolved.timeoutMs);

      try {
        const response = await fetch(resolved.url, {
          ...init,
          headers: resolved.headers,
          signal: controller.signal,
        });

        if (attempt < maxRetries && retryOn(response)) {
          const retryAfter = parseRetryAfter(response.headers.get("retry-after"));
          const delay =
            retryAfter ?? computeBackoff(attempt, options.backoff, options.backoff?.cap);
          options.onRetry?.(attempt + 1, response);
          await sleep(delay);
          continue;
        }

        return response;
      } catch (error) {
        lastError = error;
        if (attempt >= maxRetries) {
          break;
        }
        options.onRetry?.(attempt + 1, error);
        await sleep(computeBackoff(attempt, options.backoff, options.backoff?.cap));
      } finally {
        clearTimeout(timer);
      }
    }

    throw lastError;
  }

  return { fetch: run };
}
