import { CardsSkeleton, TableSkeleton } from "@/components/shared/skeletons";

export default function InsightsLoading() {
  return (
    <div className="space-y-6">
      <CardsSkeleton count={5} />
      <TableSkeleton rows={8} />
    </div>
  );
}
