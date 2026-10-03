"use server";
import { redirect } from "next/navigation";
import { publicApi } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/errors";
import { clearSession, getRefreshToken, saveSession } from "@/lib/session";
import type { TokenResponse } from "@/types/models";

export type LoginState = { error: string | null };

export async function login(_previous: LoginState, formData: FormData): Promise<LoginState> {
  const username = String(formData.get("username") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  if (username === "" || password === "") {
    return { error: "Please enter your username and password." };
  }

  try {
    const tokens = await publicApi<TokenResponse>("/auth/login", { method: "POST", body: { username, password } });
    await saveSession(tokens.accessToken, tokens.refreshToken, tokens.expiresIn);
  } catch (error) {
    return { error: errorMessage(error) };
  }
  redirect("/dashboard");
}

export async function logout() {
  const refreshToken = await getRefreshToken();
  if (refreshToken) {
    try {
      await publicApi("/auth/logout", { method: "POST", body: { refresh_token: refreshToken } });
    } catch {
      // The session is removed from this browser either way.
    }
  }
  await clearSession();
  redirect("/login");
}
