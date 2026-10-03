import { ApiError } from "./errors";

export type Safe<T> = { data: T | null; error: string | null; status: number | null };

/**
 * Runs an API call and turns a failure into a value, so a page can show a friendly message
 * instead of crashing:   const { data, error } = await safe(() => getRisk(...));
 * Redirects (for example to the login page) are NOT swallowed.
 */
export async function safe<T>(call: () => Promise<T>): Promise<Safe<T>> {
  try {
    return { data: await call(), error: null, status: null };
  } catch (error) {
    if (error instanceof ApiError) {
      return { data: null, error: error.message, status: error.status };
    }
    throw error;
  }
}
