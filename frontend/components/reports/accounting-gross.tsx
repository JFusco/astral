import type { Accounting } from "@/lib/contracts";
import { ui } from "@/lib/ui";
import { Panel, label } from "../primitives";
export function AccountingGross({ r }: { r: Accounting }) {
  return (
    <Panel
      title="Gross matches by book"
      subtitle="Before fees · retained source records"
    >
      <div className={`${ui.panelBody} overflow-x-auto`}>
        <p>
          {label(r.gross_fifo_diagnostics.status)}.{" "}
          {r.gross_fifo_diagnostics.basis}
        </p>
        {r.gross_fifo_diagnostics.by_book.length ? (
          <table className={ui.table}>
            <thead>
              <tr>
                <th>ASSET</th>
                <th>BOOK</th>
                <th>GROSS REALIZED USD</th>
              </tr>
            </thead>
            <tbody>
              {r.gross_fifo_diagnostics.by_book.map((b, i) => (
                <tr key={i}>
                  <td>{b.symbol}</td>
                  <td>{b.book}</td>
                  <td>{b.gross_realized_usd}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No gross lot matches recorded.</p>
        )}
      </div>
    </Panel>
  );
}
