"use client";
import type { Dashboard } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { display } from "@/lib/format";
import { Evidence } from "../ui/evidence";
import { SourceLink } from "../ui/source-link";
import { Dialog } from "../dialog";
export function PacketDialog({
  selected,
  onClose,
}: {
  selected: Dashboard["research"]["packets"][number];
  onClose: () => void;
}) {
  return (
    <Dialog
      title={`${selected.symbol}: why now?`}
      eyebrow="RESEARCH EVIDENCE / NO EXECUTION"
      onClose={onClose}
    >
      <p>
        As of {selected.as_of}. Expires {selected.expires_at}.
      </p>
      <Evidence value={selected.facts} />
      <div className={ui.notice}>
        {selected.vetoes.length
          ? selected.vetoes.map((v) => <p key={v}>◇ {v}</p>)
          : "Evidence gate passed; this is still a research proposal."}
      </div>
      {selected.evidence.map((e, i) => (
        <div key={i} className="border-b border-line py-3 text-caption">
          <p>
            {display(e.id)} · {display(e.headline ?? e.source)}
          </p>
          <p>{display(e.at ?? e.published_at)}</p>
          <SourceLink url={e.url ?? e.source} />
        </div>
      ))}
      <p className="break-all text-xxs">
        Input {selected.input_hash}. News is untrusted evidence. No model may
        remove a veto or submit an order. Calendar coverage is independent of
        news coverage.
      </p>
    </Dialog>
  );
}
