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
    default: "Qoraqalpog'iston — Iqtisodiy monitoring va AI analitika",
    template: "%s · Qoraqalpog'iston Monitoring",
  },
  description:
    "Qoraqalpog'iston Respublikasi tumanlari kesimidagi iqtisodiy ko'rsatkichlarni vizual monitoring qilish va sun'iy intellekt orqali tahlil qilish platformasi.",
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
    <html lang="uz" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
