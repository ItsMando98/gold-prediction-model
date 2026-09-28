import type { Metadata } from "next";
import { ThemeToggle } from "@/components/ThemeToggle";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gold Prediction Model",
  description: "Gold Market Intelligence & Prediction System",
};

// Applies a stored theme before paint, so there's no light->dark flash on load.
const themeInitScript = `
(function () {
  try {
    var t = localStorage.getItem("theme");
    if (t === "light" || t === "dark") {
      document.documentElement.setAttribute("data-theme", t);
    }
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>
        <div className="shell">
          <div className="topbar">
            <div className="brand">
              <h1>Gold Prediction Model</h1>
              <span className="subtitle">Gold Market Intelligence &amp; Prediction System</span>
            </div>
            <ThemeToggle />
          </div>
          {children}
        </div>
      </body>
    </html>
  );
}
