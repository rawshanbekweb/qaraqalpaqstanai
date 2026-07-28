import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Qaraqalpaqstan — Ekonomikalıq monitoring hám AI analitika",
    template: "%s · Qaraqalpaqstan Monitoring",
  },
  description:
    "Qaraqalpaqstan Respublikası rayonları keseginde ekonomikalıq kórsetkishlerdi vizual monitoring etiw hám jasalma intellekt arqalı analiz etiw platforması.",
};

export const viewport: Viewport = {
  themeColor: "#04060f",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="kaa" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
