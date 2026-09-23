import React from "react";

interface TableProps {
  children: React.ReactNode;
  className?: string;
}

export const Table = ({ children, className = "" }: TableProps) => {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="min-w-full divide-y divide-gray-200">
        {children}
      </table>
    </div>
  );
}

export const TableHead = ({ children }: { children: React.ReactNode }) => {
  return <thead className="bg-gray-50">{children}</thead>;
}

export const TableBody = ({ children }: { children: React.ReactNode }) => {
  return <tbody className="bg-white divide-y divide-gray-200">{children}</tbody>;
}

export const TableRow = ({ children }: { children: React.ReactNode }) => {
  return <tr>{children}</tr>;
}

export const TableHeader = ({ children }: { children: React.ReactNode }) => {
  return (
    <th
      scope="col"
      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
    >
      {children}
    </th>
  );
}

export const TableCell = ({
  children,
  className = "",
  ...rest
}: React.TdHTMLAttributes<HTMLTableCellElement>) => {
  return (
    <td
      className={`px-6 py-4 whitespace-nowrap text-sm text-gray-500 ${className}`}
      {...rest}
    >
      {children}
    </td>
  );
}
