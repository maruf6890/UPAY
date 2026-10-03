"use client";
import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";

export const RouteMapLoader = dynamic(() => import("./route-map").then((module) => module.RouteMap), {
  ssr: false,
  loading: () => <Skeleton className="h-[420px] w-full rounded-xl" />,
});
