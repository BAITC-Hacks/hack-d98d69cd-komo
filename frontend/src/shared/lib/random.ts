// getRandomValues also works on HTTP development hosts where randomUUID is absent.
export function randomToken(): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('');
}
