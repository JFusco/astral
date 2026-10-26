"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
/** Marks the current route; the only browser-dependent part of navigation. */
export function NavLink({
  href,
  className,
  title,
  children,
}: {
  href: string;
  className: string;
  title?: string;
  children: ReactNode;
}) {
  const path = usePathname();
  return (
    <Link
      href={href}
      className={className}
      aria-label={title}
      title={title}
      aria-current={path === href ? "page" : undefined}
    >
      {children}
    </Link>
  );
}
