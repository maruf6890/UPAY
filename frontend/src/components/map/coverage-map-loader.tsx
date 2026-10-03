"use client";
import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";

/** The map needs the browser (WebGL), so it is loaded there only. */
export const CoverageMapLoader = dynamic(() => import("./coverage-map").then((module) => module.CoverageMap), {
  ssr: false,
  loading: () => <Skeleton className="h-[520px] w-full rounded-xl" />,
});
