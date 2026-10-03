import "server-only";
import { cookies } from "next/headers";
import { ACCESS_COOKIE, AS_OF_COOKIE, REFRESH_COOKIE, accessCookieOptions, preferenceCookieOptions, refreshCookieOptions } from "@/lib/cookies";

/** Reads the login token. Used by privateApi. */
export async function getAccessToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(ACCESS_COOKIE)?.value;
}

export async function getRefreshToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(REFRESH_COOKIE)?.value;
}

/** Saves the tokens after login. Only works inside a Server Action or Route Handler. */
export async function saveSession(accessToken: string, refreshToken: string, expiresIn: number) {
  const store = await cookies();
  store.set(ACCESS_COOKIE, accessToken, accessCookieOptions(expiresIn));
  store.set(REFRESH_COOKIE, refreshToken, refreshCookieOptions());
}

export async function clearSession() {
  const store = await cookies();
  store.delete(ACCESS_COOKIE);
  store.delete(REFRESH_COOKIE);
}

/** The "demo date" the user picked in the top bar. undefined means: let the backend choose its default. */
export async function getAsOf(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(AS_OF_COOKIE)?.value;
}

export async function saveAsOf(value: string | null) {
  const store = await cookies();
  if (value === null) {
    store.delete(AS_OF_COOKIE);
  } else {
    store.set(AS_OF_COOKIE, value, preferenceCookieOptions());
  }
}
