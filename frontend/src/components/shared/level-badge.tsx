import { Badge } from "@/components/ui/badge";
import { levelTone } from "@/lib/format";
import { humanize } from "@/lib/format";

/** HIGH is red, MEDIUM is amber, LOW is green. */
export function LevelBadge({ level }: { level: string }) {
  return <Badge variant={levelTone(level)}>{humanize(level)}</Badge>;
}
