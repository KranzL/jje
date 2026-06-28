import { BackoffOptions, DEFAULT_BACKOFF } from "./types";

export function computeBackoff(
  attempt: number,
  options: BackoffOptions = DEFAULT_BACKOFF,
  cap?: number,
): number {
  const base = options.base ?? DEFAULT_BACKOFF.base;
  const factor = options.factor ?? DEFAULT_BACKOFF.factor;
  const ceiling = cap ?? options.cap;

  const safeAttempt = Math.max(0, attempt);
  let delay = base * Math.pow(factor, safeAttempt);

  if (ceiling !== undefined) {
    delay = Math.min(delay, ceiling);
  }

  if (options.jitter ?? DEFAULT_BACKOFF.jitter) {
    delay = delay * (0.5 + Math.random() * 0.5);
  }

  return Math.round(delay);
}

export function parseRetryAfter(header: string | null): number | null {
  if (header === null) {
    return null;
  }

  const trimmed = header.trim();
  const seconds = Number(trimmed);
  if (!Number.isNaN(seconds)) {
    return seconds * 1000;
  }

  const date = Date.parse(trimmed);
  if (!Number.isNaN(date)) {
    return Math.max(0, date - Date.now());
  }

  return null;
}
