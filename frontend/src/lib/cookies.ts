/** Read a cookie the server made readable (only csrf_token; auth cookies are httpOnly). */
export function readCookie(name: string): string | undefined {
  const prefix = `${name}=`;
  const match = document.cookie.split("; ").find((part) => part.startsWith(prefix));
  return match ? decodeURIComponent(match.slice(prefix.length)) : undefined;
}
