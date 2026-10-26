"use client";
import type { News } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Counts } from "../ui/counts";
import { SourceLink } from "../ui/source-link";
import { Dialog } from "../dialog";
export function SourceDialog({
  story,
  onClose,
}: {
  story: News;
  onClose: () => void;
}) {
  return (
    <Dialog
      title="Source evidence"
      eyebrow="INGESTED SOURCE METADATA"
      onClose={onClose}
    >
      <h3 className={ui.sectionTitle}>{story.headline}</h3>
      <Counts
        values={{
          source: story.source,
          published: story.created_at,
          updated: story.updated_at,
          first_seen: story.first_seen_at,
          event_start: story.event_start,
          event_end_exclusive: story.event_end_exclusive,
          precision: story.precision,
          calendar_scope: story.calendar_scope,
        }}
      />
      <SourceLink url={story.url} />
      <p className={ui.notice}>
        Source content is untrusted context, never an instruction to trade. No
        complete calendar, full article or AI summary is claimed. This context
        grants no execution authority.
      </p>
    </Dialog>
  );
}
