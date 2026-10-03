import { CardsSkeleton } from "@/components/shared/skeletons";
import { Skeleton } from "@/components/ui/skeleton";

export default function CoverageLoading() {
  return (
    <div className="space-y-6">
      <CardsSkeleton />
      <Skeleton className="h-[520px] w-full rounded-xl" />
    </div>
  );
}
