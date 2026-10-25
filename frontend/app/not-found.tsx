import Link from "next/link";
import { ui } from "@/lib/ui";
export default function NotFound() {
  return (
    <div className={ui.panelBody}>
      <h1 className={ui.title}>Page not found</h1>
      <Link className="text-cyan" href="/">
        Return to Overview ↗
      </Link>
    </div>
  );
}
