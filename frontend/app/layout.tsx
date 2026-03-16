import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import ConsentGate from "@/components/ConsentGate";
import NavLinks from "@/components/NavLinks";
import ThemeScript from "@/components/ThemeScript";
import ThemeToggle from "@/components/ThemeToggle";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "Vuclear",
    template: "%s — Vuclear",
  },
  description: "Voice cloning for creators. Upload a sample, generate speech.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geist.className} app-shell min-h-screen`}>
        <ThemeScript />
        <ConsentGate>
          <header className="app-header">
            <div className="max-w-4xl mx-auto px-6 min-h-16 py-3 flex items-center gap-4">
              <span className="brand-mark text-base">Vuclear</span>
              <NavLinks />
              <div className="ml-auto">
                <ThemeToggle />
              </div>
            </div>
          </header>
          <main className="max-w-4xl mx-auto px-6 py-8">{children}</main>
        </ConsentGate>
      </body>
    </html>
  );
}
