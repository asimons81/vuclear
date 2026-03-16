import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import ConsentGate from "@/components/ConsentGate";
import NavLinks from "@/components/NavLinks";
import ThemeScript from "@/components/ThemeScript";
import ThemeToggle from "@/components/ThemeToggle";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Vuclear",
    template: "%s — Vuclear",
  },
  description: "Voice cloning for creators. Upload a sample, generate speech.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <body className={`${inter.className} app-shell min-h-screen bg-background text-foreground font-sans antialiased`}>
        <ThemeScript />
        <ConsentGate>
          <header className="app-header">
            <div className="max-w-5xl mx-auto px-6 min-h-16 py-3 flex items-center gap-4">
              <div className="brand-lockup">
                <span className="brand-mark" aria-hidden="true">
                  <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path
                      d="M8 2C8 2 3 4.5 3 8.5C3 10.985 5.015 13 7.5 13H8.5C10.985 13 13 10.985 13 8.5C13 4.5 8 2 8 2Z"
                      fill="white"
                      fillOpacity="0.92"
                    />
                    <circle cx="8" cy="8.5" r="2" fill="#0c0c0e" />
                  </svg>
                </span>
                <span className="brand-name">Vuclear</span>
              </div>
              <NavLinks />
              <div className="ml-auto">
                <ThemeToggle />
              </div>
            </div>
          </header>
          <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
        </ConsentGate>
      </body>
    </html>
  );
}
