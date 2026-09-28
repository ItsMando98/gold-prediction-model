import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gold Prediction Model",
  description: "Gold Market Intelligence & Prediction System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}
