import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

/** Placeholders shown while the server is fetching data. */

export function CardsSkeleton({ count = 4 }: { count?: number }) {
  const items = Array.from({ length: count }, (_, index) => index);
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((item) => (
        <Card key={item} className="gap-3 py-4">
          <div className="px-5">
            <Skeleton className="h-3 w-24" />
          </div>
          <div className="px-5">
            <Skeleton className="h-7 w-20" />
          </div>
        </Card>
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  const items = Array.from({ length: rows }, (_, index) => index);
  return (
    <Card className="gap-0 py-0">
      <div className="border-b px-5 py-4">
        <Skeleton className="h-4 w-40" />
      </div>
      {items.map((item) => (
        <div key={item} className="flex items-center gap-4 border-b px-5 py-3.5 last:border-0">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-16" />
        </div>
      ))}
    </Card>
  );
}

export function ChartSkeleton() {
  return (
    <Card>
      <div className="px-5">
        <Skeleton className="h-4 w-48" />
      </div>
      <div className="px-5">
        <Skeleton className="h-[260px] w-full" />
      </div>
    </Card>
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-6">
      <CardsSkeleton />
      <TableSkeleton />
    </div>
  );
}
