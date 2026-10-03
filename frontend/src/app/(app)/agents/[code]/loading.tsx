import { CardsSkeleton, ChartSkeleton } from "@/components/shared/skeletons";

export default function AgentLoading() {
  return (
    <div className="space-y-6">
      <CardsSkeleton />
      <ChartSkeleton />
    </div>
  );
}
