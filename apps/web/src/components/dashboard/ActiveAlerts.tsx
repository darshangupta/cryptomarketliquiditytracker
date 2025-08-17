"use client";

import { AlertTriangle, CheckCircle } from "lucide-react";
import { Alert } from "./types";

interface ActiveAlertsProps {
  alerts: Alert[];
}

export function ActiveAlerts({ alerts }: ActiveAlertsProps) {
  const activeAlerts = alerts.filter(alert => alert.isActive);
  
  if (activeAlerts.length === 0) return null;

  return (
    <div className="space-y-2">
      {activeAlerts.map(alert => (
        <div 
          key={alert.id}
          className={`border rounded-lg p-4 ${
            alert.severity === "high" 
              ? "bg-red-50 border-red-200" 
              : alert.severity === "medium"
              ? "bg-yellow-50 border-yellow-200"
              : "bg-blue-50 border-blue-200"
          }`}
        >
          <div className="flex items-center space-x-2">
            {alert.severity === "high" ? (
              <AlertTriangle className="w-5 h-5 text-red-600" />
            ) : alert.severity === "medium" ? (
              <AlertTriangle className="w-5 h-5 text-yellow-600" />
            ) : (
              <CheckCircle className="w-5 h-5 text-blue-600" />
            )}
            <span className={`font-semibold ${
              alert.severity === "high" ? "text-red-800" :
              alert.severity === "medium" ? "text-yellow-800" : "text-blue-800"
            }`}>
              {alert.type.charAt(0).toUpperCase() + alert.type.slice(1)} Alert
            </span>
            <span className="text-sm text-gray-500">({alert.timestamp})</span>
          </div>
          <p className={`mt-1 ${
            alert.severity === "high" ? "text-red-700" :
            alert.severity === "medium" ? "text-yellow-700" : "text-blue-700"
          }`}>
            {alert.message}
          </p>
        </div>
      ))}
    </div>
  );
}
