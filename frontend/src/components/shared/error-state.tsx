import { CircleAlert, ServerCrash } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

type ErrorStateProps = { message: string; status?: number | null; title?: string };

/** Shown when the backend could not give us the data. */
export function ErrorState({ message, status, title = "We couldn't load this" }: ErrorStateProps) {
  const backendDown = status === 0;
  const Icon = backendDown ? ServerCrash : CircleAlert;
  return (
    <Alert variant="danger">
      <Icon />
      <AlertTitle>{backendDown ? "The server is not reachable" : title}</AlertTitle>
      <AlertDescription>
        {message}
        {backendDown ? <span className="mt-1 block text-xs">Start the FastAPI backend, then refresh this page.</span> : null}
      </AlertDescription>
    </Alert>
  );
}
