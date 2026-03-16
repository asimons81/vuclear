import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import ConsentGate from "@/components/ConsentGate";
import NavLinks from "@/components/NavLinks";

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
    <html lang="en">
      <body className={`${geist.className} bg-slate-50 text-slate-900 min-h-screen`}>
        <ConsentGate>
          <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-40">
            <div className="max-w-4xl mx-auto px-6 h-14 flex items-center gap-8">
              <span className="font-semibold text-white text-base tracking-tight">Vuclear</span>
              <NavLinks />
            </div>
          </header>
          <main className="max-w-4xl mx-auto px-6 py-8">{children}</main>
        </ConsentGate>
      </body>
    </html>
  );
}
