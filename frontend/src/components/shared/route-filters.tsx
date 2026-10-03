"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type RouteFiltersProps = { districts: string[]; district: string; capacity: number; maxStops: number };

/** A plain GET form: submitting it reloads the page with ?district=...&capacity=...&stops=... */
export function RouteFilters({ districts, district, capacity, maxStops }: RouteFiltersProps) {
  const [selected, setSelected] = useState(district);
  return (
    <form action="/route" method="get" className="flex flex-wrap items-end gap-3 rounded-xl border bg-card p-4">
      <input type="hidden" name="district" value={selected} />
      <div className="space-y-1.5">
        <Label>District (one DSO, one van)</Label>
        <Select value={selected} onValueChange={setSelected}>
          <SelectTrigger className="w-[190px]" aria-label="District">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {districts.map((item) => (
              <SelectItem key={item} value={item}>
                {item}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="capacity">Van cash capacity (BDT)</Label>
        <Input id="capacity" name="capacity" type="number" min={1} step={100000} defaultValue={capacity} className="w-[190px]" />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="stops">Max stops</Label>
        <Input id="stops" name="stops" type="number" min={1} max={40} defaultValue={maxStops} className="w-24" />
      </div>
      <Button type="submit">Plan route</Button>
    </form>
  );
}
