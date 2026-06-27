export interface TokenClaims {
  sub: string;
  scope: string[];
  exp: number;
}

export async function parseToken(raw: string): Promise<TokenClaims> {
  const parts = raw.split(".");
  if (parts.length !== 3) {
    throw new Error("malformed token");
  }
  const payload = Buffer.from(parts[1], "base64url").toString("utf8");
  const json = JSON.parse(payload) as Partial<TokenClaims>;
  return {
    sub: String(json.sub ?? ""),
    scope: json.scope ?? [],
    exp: Number(json.exp ?? 0),
  };
}
