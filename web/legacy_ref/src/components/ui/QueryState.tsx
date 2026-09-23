import React from "react";
import { Link } from "react-router-dom";

export const LoadingState = ({ label = "Memuat data..." }: { label?: string }) => (
  <div className="flex h-64 items-center justify-center">
    <p className="text-gray-500">{label}</p>
  </div>
);

export const ErrorState = ({ label = "Gagal memuat data." }: { label?: string }) => (
  <div className="flex h-64 items-center justify-center">
    <p className="text-red-500">{label}</p>
  </div>
);

interface EmptyTableRowProps {
  colSpan: number;
  label: string;
}

/**
 * Baris "kosong" untuk dipakai di dalam <TableBody> — selalu diberi colSpan
 * agar melebar penuh, tidak seperti bug lama yang menyisakan sel tunggal.
 */
export const EmptyTableRow = ({ colSpan, label }: EmptyTableRowProps) => (
  <tr>
    <td colSpan={colSpan} className="px-6 py-4 text-center text-sm text-gray-500">
      {label}
    </td>
  </tr>
);

const STAT_COLOR_CLASSES = {
  indigo: "text-indigo-600",
  blue: "text-blue-600",
  green: "text-green-600",
  red: "text-red-600",
  yellow: "text-yellow-600",
} as const;

export const StatCard = ({
  title,
  value,
  color = "indigo",
  hint,
  linkTo,
  linkLabel,
  footer,
}: {
  title: string;
  value?: React.ReactNode;
  color?: keyof typeof STAT_COLOR_CLASSES;
  hint?: string;
  linkTo?: string;
  linkLabel?: string;
  footer?: React.ReactNode;
}) => (
  <div className="rounded-lg border border-gray-200 bg-white p-6 shadow">
    <h2 className="mb-4 text-lg font-bold text-gray-800">{title}</h2>
    {value !== undefined && <p className={`text-3xl font-semibold ${STAT_COLOR_CLASSES[color]}`}>{value}</p>}
    {hint && <p className="mb-4 text-sm text-gray-500">{hint}</p>}
    {footer}
    {linkTo && linkLabel && (
      <Link to={linkTo} className="text-sm text-indigo-600 hover:underline">
        {linkLabel} &rarr;
      </Link>
    )}
  </div>
);
