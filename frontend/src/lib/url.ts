/** Builds a link such as /risk?level=HIGH&district=Sylhet, leaving out empty values. */
export function buildHref(path: string, params: Record<string, string | undefined>): string {
  const search = new URLSearchParams();
  for (const key of Object.keys(params)) {
    const value = params[key];
    if (value !== undefined && value !== "") {
      search.set(key, value);
    }
  }
  const text = search.toString();
  return text ? `${path}?${text}` : path;
}
