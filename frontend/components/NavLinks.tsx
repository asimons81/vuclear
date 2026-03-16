"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Voices" },
  { href: "/studio", label: "Studio" },
  { href: "/history", label: "History" },
];

export default function NavLinks() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-1" aria-label="Main navigation">
      {NAV_ITEMS.map(({ href, label }) => {
        const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={`nav-link px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              isActive ? "nav-link-active" : ""
            }`}
            aria-current={isActive ? "page" : undefined}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
