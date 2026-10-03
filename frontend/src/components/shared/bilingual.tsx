"use client";
import { useUiStore } from "@/store/ui-store";

type BilingualProps = { en: string; bn: string; className?: string };

/** Shows the English or the Bangla text, depending on the language switch in the top bar. */
export function Bilingual({ en, bn, className }: BilingualProps) {
  const language = useUiStore((state) => state.language);
  return (
    <span className={className} lang={language}>
      {language === "bn" ? bn : en}
    </span>
  );
}
