import { HeaderMap } from "./types";

export function normalizeHeaders(headers: HeaderMap): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(headers)) {
    out[key.toLowerCase()] = Array.isArray(value) ? value.join(", ") : value;
  }
  return out;
}

export function mergeHeaders(
  base: HeaderMap | undefined,
  override: HeaderMap | undefined,
): Record<string, string> {
  return {
    ...normalizeHeaders(base ?? {}),
    ...normalizeHeaders(override ?? {}),
  };
}

export function hasHeader(
  headers: Record<string, string>,
  name: string,
): boolean {
  return Object.prototype.hasOwnProperty.call(headers, name.toLowerCase());
}
