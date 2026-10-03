"use server";
import { revalidatePath } from "next/cache";
import { saveAsOf } from "@/lib/session";

/** Remembers the demo date picked in the top bar. "default" removes it. */
export async function setDemoDate(value: string) {
  await saveAsOf(value === "default" ? null : value);
  revalidatePath("/", "layout");
}
