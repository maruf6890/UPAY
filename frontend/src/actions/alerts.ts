"use server";
import { revalidatePath } from "next/cache";
import { privateApi } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/errors";

export type ReviewState = { ok: boolean; message: string | null };

/** Confirm or dismiss an alert. The backend records the logged-in user as the reviewer. */
export async function reviewAlert(_previous: ReviewState, formData: FormData): Promise<ReviewState> {
  const alertId = String(formData.get("alertId") ?? "");
  const decision = String(formData.get("decision") ?? "");
  const note = String(formData.get("note") ?? "").trim();

  if (alertId === "" || (decision !== "confirmed" && decision !== "dismissed")) {
    return { ok: false, message: "Choose confirm or dismiss." };
  }

  try {
    await privateApi(`/alerts/${alertId}/review`, {
      method: "POST",
      body: { decision, note: note === "" ? null : note },
    });
  } catch (error) {
    return { ok: false, message: errorMessage(error) };
  }

  revalidatePath("/alerts");
  revalidatePath("/dashboard");
  return { ok: true, message: decision === "confirmed" ? "Marked as confirmed." : "Dismissed." };
}

export type ExplainResult = { text: string | null; generatedBy: string | null; error: string | null };

/** The plain-language explanation of one alert. */
export async function explainAlert(alertId: string): Promise<ExplainResult> {
  try {
    const result = await privateApi<{ narrative: string; generatedBy: string }>(`/alerts/${alertId}/narrative`);
    return { text: result.narrative, generatedBy: result.generatedBy, error: null };
  } catch (error) {
    return { text: null, generatedBy: null, error: errorMessage(error) };
  }
}
