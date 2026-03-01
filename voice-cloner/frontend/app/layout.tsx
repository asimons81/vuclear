import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import ConsentGate from "@/components/ConsentGate";
import Link from "next/link";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Voice Cloner",
  description: "Local-first voice cloning — upload a sample, get a voice.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geist.className} bg-gray-50 text-gray-900 min-h-screen`}>
        <ConsentGate>
          <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
            <nav
              className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-6"
              aria-label="Main navigation"
            >
              <span className="font-bold text-indigo-600 text-lg">Voice Cloner</span>
              <Link
                href="/"
                className="text-sm font-medium text-gray-600 hover:text-indigo-600 transition-colors"
              >
                Voices
              </Link>
              <Link
                href="/studio"
                className="text-sm font-medium text-gray-600 hover:text-indigo-600 transition-colors"
              >
                Studio
              </Link>
              <Link
                href="/history"
                className="text-sm font-medium text-gray-600 hover:text-indigo-600 transition-colors"
              >
                History
              </Link>
            </nav>
          </header>
          <main className="max-w-4xl mx-auto px-4 py-8">{children}</main>
        </ConsentGate>
      </body>
    </html>
  );
}
