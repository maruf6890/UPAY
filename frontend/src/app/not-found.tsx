import Link from "next/link";
import { SearchX } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 px-6 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-subtle text-muted-foreground">
        <SearchX className="size-6" />
      </div>
      <h1 className="text-xl font-semibold">Page not found</h1>
      <p className="max-w-sm text-sm text-muted-foreground">We could not find what you were looking for.</p>
      <Button asChild>
        <Link href="/dashboard">Back to the dashboard</Link>
      </Button>
    </div>
  );
}
