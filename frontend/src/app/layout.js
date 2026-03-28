import "./globals.css";

export const metadata = {
  title: "Job Discovery",
  description: "Job discovery and application tracking platform",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
