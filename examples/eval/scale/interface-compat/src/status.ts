const RETRYABLE_STATUS = new Set([408, 425, 429, 500, 502, 503, 504]);

export function isRetryableStatus(status: number): boolean {
  return RETRYABLE_STATUS.has(status);
}

export function defaultRetryOn(response: Response): boolean {
  return isRetryableStatus(response.status);
}
