import { CardsSkeleton, TableSkeleton } from "@/components/shared/skeletons";

export default function RouteLoading() {
  return (
    <div className="space-y-6">
      <CardsSkeleton />
      <TableSkeleton rows={6} />
    </div>
  );
}
