"use client";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type DistrictFilterProps = { districts: string[]; value: string | undefined };

/** Changes the ?district= part of the address. The server then loads the data for that district. */
export function DistrictFilter({ districts, value }: DistrictFilterProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function change(next: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "all") {
      params.delete("district");
    } else {
      params.set("district", next);
    }
    const text = params.toString();
    router.push(text ? `${pathname}?${text}` : pathname);
  }

  return (
    <Select value={value ?? "all"} onValueChange={change}>
      <SelectTrigger className="w-[190px]" aria-label="District">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All districts</SelectItem>
        {districts.map((district) => (
          <SelectItem key={district} value={district}>
            {district}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
