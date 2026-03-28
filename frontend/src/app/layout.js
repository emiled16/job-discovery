import "./globals.css";

export const metadata = {
  title: "Job Discovery",
  description: "Platform bootstrap",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

