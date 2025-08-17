"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle } from "lucide-react";
import { Alert, AlertSettings } from "./types";

interface AlertCenterProps {
  alerts: Alert[];
  alertSettings: AlertSettings;
  onAlertSettingsChange: (settings: AlertSettings) => void;
}

export function AlertCenter({ alerts, alertSettings, onAlertSettingsChange }: AlertCenterProps) {
  const handleSettingChange = (key: keyof AlertSettings, value: number) => {
    onAlertSettingsChange({
      ...alertSettings,
      [key]: value,
    });
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Alert Settings</CardTitle>
          <CardDescription>Configure alert thresholds</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium">Spread Threshold ($)</label>
              <input
                type="number"
                value={alertSettings.spreadThreshold}
                onChange={(e) => handleSettingChange("spreadThreshold", Number(e.target.value))}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Price Change Threshold (%)</label>
              <input
                type="number"
                value={alertSettings.priceChangeThreshold}
                onChange={(e) => handleSettingChange("priceChangeThreshold", Number(e.target.value))}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Min Arbitrage Profit ($)</label>
              <input
                type="number"
                value={alertSettings.arbitrageMinProfit}
                onChange={(e) => handleSettingChange("arbitrageMinProfit", Number(e.target.value))}
                className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Alert History</CardTitle>
          <CardDescription>Recent alerts and notifications</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {alerts.length > 0 ? (
              alerts.map(alert => (
                <div 
                  key={alert.id}
                  className={`p-3 rounded-lg border ${
                    alert.severity === "high" 
                      ? "bg-red-50 border-red-200" 
                      : alert.severity === "medium"
                      ? "bg-yellow-50 border-yellow-200"
                      : "bg-blue-50 border-blue-200"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {alert.severity === "high" ? (
                        <AlertTriangle className="w-4 h-4 text-red-600" />
                      ) : alert.severity === "medium" ? (
                        <AlertTriangle className="w-4 h-4 text-yellow-600" />
                      ) : (
                        <CheckCircle className="w-4 h-4 text-blue-600" />
                      )}
                      <span className="text-sm font-medium capitalize">{alert.type}</span>
                      <Badge variant={alert.severity === "high" ? "destructive" : "secondary"}>
                        {alert.severity}
                      </Badge>
                    </div>
                    <span className="text-xs text-gray-500">{alert.timestamp}</span>
                  </div>
                  <p className="mt-1 text-sm">{alert.message}</p>
                </div>
              ))
            ) : (
              <div className="text-center text-gray-500 py-8">
                <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
                <p>No alerts yet</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
