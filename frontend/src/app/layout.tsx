import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthHydrator } from "@/components/auth-hydrator";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Facial Analysis",
  description: "AI-driven facial aesthetics analysis platform.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      {/* suppressHydrationWarning here too (not just on <html>): browser
          extensions like Grammarly inject attributes (data-gr-ext-installed,
          data-new-gr-c-s-check-loaded) onto <body> before React hydrates,
          which otherwise trips a hydration-mismatch warning on every load
          for anyone with the extension installed. This only suppresses the
          warning for body's OWN attributes/text -- it does not hide
          mismatches in any child content, so real bugs still surface. */}
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        {/* Locked to light: the product's design language is a light,
            soft-grey surface (never black) -- see globals.css's --background
            token. enableSystem is intentionally off so OS dark-mode
            preference can't override that. */}
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false} disableTransitionOnChange>
          <AuthHydrator />
          {children}
          <Toaster position="top-right" richColors />
        </ThemeProvider>
      </body>
    </html>
  );
}
