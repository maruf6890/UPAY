"use server";
import { privateApi } from "@/lib/api/client";
import { errorMessage } from "@/lib/api/errors";
import { emptyAskState, type AskState } from "@/lib/ask-state";
import { getAsOf } from "@/lib/session";

export async function askCopilot(_previous: AskState, formData: FormData): Promise<AskState> {
  const question = String(formData.get("question") ?? "").trim();
  if (question.length < 3) {
    return { ...emptyAskState, question, error: "Please type a question (at least 3 characters)." };
  }
  if (question.length > 300) {
    return { ...emptyAskState, question, error: "Please keep the question under 300 characters." };
  }

  try {
    const result = await privateApi<{ answer: string; toolsUsed: { tool: string }[]; generatedBy: string }>("/copilot/ask", {
      method: "POST",
      body: { question, as_of: await getAsOf() ?? null },
    });
    return { question, answer: result.answer, toolsUsed: result.toolsUsed, generatedBy: result.generatedBy, error: null };
  } catch (error) {
    return { ...emptyAskState, question, error: errorMessage(error) };
  }
}
