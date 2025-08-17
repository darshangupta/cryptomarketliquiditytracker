"use client";

interface ErrorDisplayProps {
  wsError: string | null;
}

export function ErrorDisplay({ wsError }: ErrorDisplayProps) {
  if (!wsError) return null;

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <div className="flex items-center space-x-2">
        <span className="font-semibold text-red-800">Connection Error:</span>
        <span className="text-red-700">{wsError}</span>
      </div>
    </div>
  );
}
