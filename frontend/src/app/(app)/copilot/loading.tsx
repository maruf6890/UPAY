import { Skeleton } from "@/components/ui/skeleton";
import { TableSkeleton } from "@/components/shared/skeletons";

export default function CopilotLoading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-40 w-full rounded-xl" />
      <TableSkeleton rows={4} />
    </div>
  );
}
