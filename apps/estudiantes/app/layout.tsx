import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DuoBot Campus · Estudiantes",
  description: "Analiza el desempeño de los estudiantes con gráficas y modelos de machine learning.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
