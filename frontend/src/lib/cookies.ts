/** Cookie names and options. Shared by the server code and by proxy.ts (which cannot use next/headers). */
export const ACCESS_COOKIE = "pulse_access";
export const REFRESH_COOKIE = "pulse_refresh";
export const AS_OF_COOKIE = "pulse_as_of";

const secure = process.env.COOKIE_SECURE === "true";
const sessionDays = Number(process.env.SESSION_DAYS ?? "7");

/** The access cookie expires slightly BEFORE the token does, so we never send an expired token. */
export function accessCookieOptions(expiresInSeconds: number) {
  return { httpOnly: true, sameSite: "lax" as const, secure, path: "/", maxAge: Math.max(expiresInSeconds - 30, 60) };
}

export function refreshCookieOptions() {
  return { httpOnly: true, sameSite: "lax" as const, secure, path: "/", maxAge: sessionDays * 24 * 60 * 60 };
}

export function preferenceCookieOptions() {
  return { httpOnly: false, sameSite: "lax" as const, secure, path: "/", maxAge: 30 * 24 * 60 * 60 };
}
