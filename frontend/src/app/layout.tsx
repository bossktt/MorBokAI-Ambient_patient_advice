import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'หมอบอก (MorBok) — ระบบสรุปคำแนะนำแพทย์และตารางยาอัตโนมัติ',
  description: 'ระบบ AI แปลงเสียงบทสนทนาแพทย์เป็นคำแนะนำภาษาไทยอ่านง่าย (ระดับ ป.5) และส่งเข้า LINE OA ผู้ป่วยและผู้ดูแล',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="th">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@600;700;800&family=Sarabun:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-[#F9F9FF] text-[#111C2C] antialiased min-h-screen font-sans">
        {children}
      </body>
    </html>
  );
}

