import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Smart Spend — Understand your money",
  description: "Upload your bank statement and get instant spending insights",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
