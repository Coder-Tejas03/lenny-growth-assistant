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
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var stored = localStorage.getItem('lenny_theme');
                  if (stored === 'light') {
                    document.documentElement.classList.remove('dark');
                  } else {
                    document.documentElement.classList.add('dark');
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="h-full bg-canvas text-content antialiased flex flex-col overflow-hidden">
        {children}
      </body>
    </html>
  );
}
