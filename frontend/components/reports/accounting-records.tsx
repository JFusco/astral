import type { Accounting } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Panel, Counts } from "../primitives";
export function AccountingRecords({ r }: { r: Accounting }) {
  return (
    <Panel title="Unresolved records">
      <div className={`${ui.panelBody} overflow-x-auto`}>
        {Object.keys(r.issues).length ? (
          <Counts values={r.issues} />
        ) : (
          <p>
            No quantity issues in this saved snapshot. Net results still require
            complete evidence.
          </p>
        )}
        {r.custody.differences.length ? (
          <table className={ui.table}>
            <thead>
              <tr>
                {[
                  "ASSET",
                  "RECORDED NET QTY",
                  "BROKER QTY",
                  "UNEXPLAINED QTY",
                ].map((v) => (
                  <th key={v}>{v}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {r.custody.differences.map((d) => (
                <tr key={d.symbol}>
                  <td>{d.symbol}</td>
                  <td>{d.recorded_net_quantity}</td>
                  <td>{d.broker_quantity}</td>
                  <td>{d.unexplained_quantity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No comparable custody differences recorded.</p>
        )}
      </div>
    </Panel>
  );
}
