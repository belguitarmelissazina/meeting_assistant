import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Meeting Assistant",
  description: "Meeting Assistant",
};

const themeInitScript = `
(function(){try{
  var t = localStorage.getItem('theme');
  if (!t) { t = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'; }
  if (t === 'dark') document.documentElement.classList.add('dark');
}catch(e){}})();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="h-screen overflow-hidden font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
