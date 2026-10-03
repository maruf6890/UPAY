/**
 * The backend sends snake_case keys (cash_topup_bdt). The frontend uses camelCase (cashTopupBdt).
 * This converter runs once, inside the API client, so no other file has to care.
 */
function toCamelCase(key: string): string {
  return key.replace(/_([a-z0-9])/g, (_match, letter: string) => letter.toUpperCase());
}

export function camelizeKeys(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(camelizeKeys);
  }
  if (value !== null && typeof value === "object") {
    const source = value as Record<string, unknown>;
    const result: Record<string, unknown> = {};
    for (const key of Object.keys(source)) {
      result[toCamelCase(key)] = camelizeKeys(source[key]);
    }
    return result;
  }
  return value;
}
