import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DuoBot Campus · Administrativo",
  description: "Analiza la operación administrativa del campus con gráficas y modelos de machine learning.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
