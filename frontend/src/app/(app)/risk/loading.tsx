import { CardsSkeleton, TableSkeleton } from "@/components/shared/skeletons";

export default function RiskLoading() {
  return (
    <div className="space-y-6">
      <CardsSkeleton count={3} />
      <TableSkeleton rows={8} />
    </div>
  );
}
