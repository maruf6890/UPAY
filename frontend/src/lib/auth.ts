import "server-only";
import { cache } from "react";
import { redirect } from "next/navigation";
import { privateApi } from "@/lib/api/client";
import type { CurrentUser, Role } from "@/types/models";

/** Who is logged in. Asked once per page load, even if several components call it. */
export const getCurrentUser = cache(async (): Promise<CurrentUser> => {
  return privateApi<CurrentUser>("/auth/me");
});

/**
 * Keeps a page for certain roles. NOTE: this only decides what the SCREENS show.
 * The backend does not restrict its endpoints by role.
 */
export async function requireRole(allowed: Role[]): Promise<CurrentUser> {
  const user = await getCurrentUser();
  if (!allowed.includes(user.role)) {
    redirect("/dashboard");
  }
  return user;
}
