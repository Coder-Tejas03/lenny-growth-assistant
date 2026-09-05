import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lenny Growth Assistant — Grounded AI for Product & Growth",
  description:
    "AI conversational assistant grounded in Lenny's Podcast transcripts with verified citations, Ship 30 essays, and dual cloud/local model support.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark h-full">
      <body className="h-full bg-surface-950 text-slate-100 antialiased flex flex-col overflow-hidden">
        {children}
      </body>
    </html>
  );
}
