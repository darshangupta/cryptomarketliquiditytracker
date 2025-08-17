"use client";

interface FooterProps {
  lastUpdate: string | null;
}

export function Footer({ lastUpdate }: FooterProps) {
  return (
    <div className="text-center text-sm text-gray-500">
      <p>Built with Next.js, Tailwind CSS, and shadcn/ui</p>
      <p>Real-time data from Binance and Kraken</p>
      {lastUpdate && (
        <p className="mt-2 text-xs">Data timestamp: {lastUpdate}</p>
      )}
    </div>
  );
}
