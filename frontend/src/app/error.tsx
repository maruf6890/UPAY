"use client";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/shared/error-state";

/** Last safety net: shown when something unexpected breaks while rendering a page. */
export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center gap-4 px-6">
      <ErrorState title="Something went wrong" message="An unexpected error stopped this page from loading. Please try again." />
      <Button onClick={reset} className="w-fit">
        Try again
      </Button>
    </div>
  );
}
