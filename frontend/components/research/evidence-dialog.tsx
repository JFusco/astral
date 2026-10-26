"use client";
import { ui } from "@/lib/ui";
import { Evidence } from "../ui/evidence";
import { Dialog } from "../dialog";
export type Detail = { title: string; eyebrow: string; value: unknown };
export function EvidenceDialog({
  detail,
  onClose,
}: {
  detail: Detail;
  onClose: () => void;
}) {
  return (
    <Dialog title={detail.title} eyebrow={detail.eyebrow} onClose={onClose}>
      <Evidence value={detail.value} />
      <p className={ui.notice}>
        Retained evidence does not grant order authority or change frozen risk
        rules. Missing values remain unknown.
      </p>
    </Dialog>
  );
}
