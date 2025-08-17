"use client";

import { Badge } from "@/components/ui/badge";
import { Wifi, WifiOff } from "lucide-react";

interface HeaderProps {
  isConnected: boolean;
  connectionStatus: "disconnected" | "connecting" | "connected";
  lastUpdate: string | null;
}

export function Header({ isConnected, connectionStatus, lastUpdate }: HeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Crypto Liquidity Tracker</h1>
        <p className="text-gray-600">Real-time multi-venue market analytics</p>
      </div>
      <div className="flex items-center space-x-4">
        <Badge variant={isConnected ? "default" : "destructive"} className="flex items-center space-x-2">
          {isConnected ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
          <span>{connectionStatus === "connected" ? "Connected" : "Disconnected"}</span>
        </Badge>
        {lastUpdate && (
          <span className="text-sm text-gray-500">Last update: {lastUpdate}</span>
        )}
      </div>
    </div>
  );
}
