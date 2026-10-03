"use client";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/shared/error-state";

/** Catches unexpected errors inside a page and keeps the menu and top bar on screen. */
export default function PageError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="space-y-4">
      <ErrorState title="Something went wrong" message="This page could not be shown. Your data is safe. Please try again." />
      <Button onClick={reset} variant="outline">
        Try again
      </Button>
    </div>
  );
}
