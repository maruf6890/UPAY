import { redirect } from "next/navigation";
import { getAccessToken } from "@/lib/session";
import { API_BASE_URL } from "./config";
import { camelizeKeys } from "./convert";
import { ApiError } from "./errors";

/**
 * THE ONLY PLACE THAT TALKS TO THE BACKEND.
 *
 *   publicApi   no login needed  (for example: log in)
 *   privateApi  sends the logged-in user's token (everything else)
 *
 * Both run on the server and use Next.js's built-in fetch. Every other file in the app
 * calls these two functions (through the small functions in src/services).
 */

export type Query = Record<string, string | number | boolean | null | undefined>;

export type ApiOptions = {
  method?: "GET" | "POST";
  query?: Query;
  body?: unknown;
};

function buildUrl(path: string, query?: Query): string {
  const url = new URL(path, API_BASE_URL);
  if (query) {
    for (const key of Object.keys(query)) {
      const value = query[key];
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/** The backend explains errors in a "detail" field. It is either a text or a list of validation problems. */
function readErrorMessage(json: unknown, status: number): string {
  if (json && typeof json === "object" && "detail" in json) {
    const detail = (json as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      const parts: string[] = [];
      for (const item of detail) {
        if (item && typeof item === "object" && "msg" in item) {
          parts.push(String((item as { msg: unknown }).msg));
        }
      }
      if (parts.length > 0) {
        return parts.join(". ");
      }
    }
  }
  if (status === 404) return "Not found.";
  if (status === 429) return "Too many attempts. Please try again later.";
  if (status === 503) return "The service is not available yet.";
  return `The server answered with an error (${status}).`;
}

async function send<T>(path: string, options: ApiOptions, token?: string): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let body: string | undefined;
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method: options.method ?? "GET",
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
    });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Please check that the backend is running.");
  }

  const text = await response.text();
  const json = text ? parseJson(text) : null;

  if (!response.ok) {
    throw new ApiError(response.status, readErrorMessage(json, response.status));
  }
  return camelizeKeys(json) as T;
}

/** A call that does not need a login. */
export async function publicApi<T>(path: string, options: ApiOptions = {}): Promise<T> {
  return send<T>(path, options);
}

/** A call made as the logged-in user. No token, or a rejected token, sends the user to the login page. */
export async function privateApi<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const token = await getAccessToken();
  if (!token) {
    redirect("/login?expired=1");
  }
  try {
    return await send<T>(path, options, token);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      redirect("/login?expired=1");
    }
    throw error;
  }
}
