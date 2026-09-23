import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export const Card = ({ children, className = "" }: CardProps) => {
  return (
    <div className={`bg-white shadow rounded-lg p-6 ${className}`}>
      {children}
    </div>
  );
}

export const CardTitle = ({ children }: { children: React.ReactNode }) => {
  return <h3 className="text-lg font-medium text-gray-900">{children}</h3>;
}

export const CardContent = ({ children, className = "" }: CardProps) => {
  return <div className={`mt-2 ${className}`}>{children}</div>;
}
