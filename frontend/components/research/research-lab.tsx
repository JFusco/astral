"use client";
import { useState } from "react";
import { z } from "zod";
import { api, errorMessage } from "@/lib/api";
import { useDashboard } from "../provider";
import { Panel } from "../ui/panel";
import { ResearchStatus } from "./research-status";
import { ResearchGates } from "./research-gates";
import { ResearchPackets } from "./research-packets";
import { ShadowDecisions } from "./shadow-decisions";
import { TimingDecisions } from "./timing-decisions";
import { ResearchExperiments } from "./research-experiments";
import { EvidenceDialog, type Detail } from "./evidence-dialog";
import { PacketDialog } from "./packet-dialog";
/** Research panel composition and the research-run request. */
export function ResearchLab() {
  const { snapshot } = useDashboard();
  const s = snapshot.state;
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [detail, setDetail] = useState<Detail | null>(null);
  const [packet, setPacket] = useState<string | null>(null);
  const running = s?.workers.some(
    (w) => w.name === "research" && w.status === "running",
  );
  async function run() {
    if (pending || running) return;
    setPending(true);
    try {
      const result = await api(
        "/api/research/run",
        z.object({ status: z.string() }),
        { body: {} },
      );
      setMessage(
        `Research ${result.status}. Results arrive through the server stream.`,
      );
    } catch (e) {
      setMessage(errorMessage(e));
    } finally {
      setPending(false);
    }
  }
  const selected = s?.research.packets.find((p) => p.symbol === packet);
  const open = (title: string, value: unknown) =>
    setDetail({ title, eyebrow: "RETAINED EVIDENCE / NO EXECUTION", value });
  return (
    <>
      <Panel
        title="Research & risk lab"
        subtitle="Evidence before execution"
        action={
          <button
            className="text-caption text-cyan disabled:text-muted"
            disabled={
              !snapshot.connected || !s?.research.enabled || running || pending
            }
            onClick={() => void run()}
          >
            {running || pending
              ? "Research in progress…"
              : "Run research review ↗"}
          </button>
        }
      >
        <ResearchStatus />
        {message ? (
          <p role="status" className="p-5 text-caption text-cyan">
            {message}
          </p>
        ) : null}
        <ResearchGates open={open} />
        <div className="grid grid-cols-1 gap-6 p-5 lg:grid-cols-2">
          <ResearchPackets onSelect={setPacket} />
          <div>
            <ShadowDecisions />
            <TimingDecisions />
          </div>
        </div>
        <ResearchExperiments open={open} />
      </Panel>
      {detail ? (
        <EvidenceDialog detail={detail} onClose={() => setDetail(null)} />
      ) : null}
      {selected ? (
        <PacketDialog selected={selected} onClose={() => setPacket(null)} />
      ) : null}
    </>
  );
}
