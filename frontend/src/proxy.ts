import { NextResponse, type NextRequest } from "next/server";
import { API_BASE_URL } from "@/lib/api/config";
import { ACCESS_COOKIE, REFRESH_COOKIE, accessCookieOptions, refreshCookieOptions } from "@/lib/cookies";

/**
 * Runs before every page. It decides three things:
 *   1. No login at all             -> go to /login
 *   2. Access token expired        -> quietly get a new one with the refresh token
 *   3. Already logged in at /login -> go to the dashboard
 */

type NewTokens = { accessToken: string; refreshToken: string; expiresIn: number };

async function refreshTokens(refreshToken: string): Promise<NewTokens | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    const json = await response.json();
    return { accessToken: json.access_token, refreshToken: json.refresh_token, expiresIn: json.expires_in };
  } catch {
    return null;
  }
}

function forgetSession(response: NextResponse) {
  response.cookies.delete(ACCESS_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
  return response;
}

export async function proxy(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;
  const isLoginPage = pathname === "/login";
  const accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;

  // The server said the session is no longer valid: forget it (this also prevents redirect loops).
  if (isLoginPage && searchParams.has("expired")) {
    return forgetSession(NextResponse.next());
  }

  if (accessToken) {
    if (isLoginPage) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    return NextResponse.next();
  }

  if (refreshToken) {
    const tokens = await refreshTokens(refreshToken);
    if (tokens) {
      // Make the new token visible to the page rendered for THIS request, and store it in the browser.
      request.cookies.set(ACCESS_COOKIE, tokens.accessToken);
      request.cookies.set(REFRESH_COOKIE, tokens.refreshToken);
      const response = isLoginPage
        ? NextResponse.redirect(new URL("/dashboard", request.url))
        : NextResponse.next({ request });
      response.cookies.set(ACCESS_COOKIE, tokens.accessToken, accessCookieOptions(tokens.expiresIn));
      response.cookies.set(REFRESH_COOKIE, tokens.refreshToken, refreshCookieOptions());
      return response;
    }
    // The refresh token no longer works: start again at the login page.
    const response = isLoginPage ? NextResponse.next() : NextResponse.redirect(new URL("/login", request.url));
    return forgetSession(response);
  }

  if (isLoginPage) {
    return NextResponse.next();
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
