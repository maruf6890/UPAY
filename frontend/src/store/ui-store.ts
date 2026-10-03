"use client";
import { create } from "zustand";

export type Language = "en" | "bn";

type UiState = {
  /** Which language the bilingual texts (advice, reasons) are shown in. */
  language: Language;
  setLanguage: (language: Language) => void;
  /** The slide-in menu on small screens. */
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
};

export const useUiStore = create<UiState>((set) => ({
  language: "en",
  setLanguage: (language) => set({ language }),
  mobileMenuOpen: false,
  setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),
}));
