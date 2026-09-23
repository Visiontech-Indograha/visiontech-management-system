import React, { useEffect, useId } from "react";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  /** "md" (default, form pendek) atau "lg" (form panjang / multi-seksi). */
  size?: "md" | "lg";
}

const SIZE_CLASSES = { md: "max-w-md", lg: "max-w-2xl" } as const;

export const Modal = ({ isOpen, onClose, title, children, size = "md" }: ModalProps) => {
  const titleId = useId();

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={`flex max-h-[90vh] w-full ${SIZE_CLASSES[size]} flex-col rounded-lg bg-white shadow-xl`}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id={titleId} className="shrink-0 border-b border-gray-100 p-6 pb-4 text-lg font-bold text-gray-900">
          {title}
        </h2>
        <div className="overflow-y-auto p-6 pt-4">{children}</div>
      </div>
    </div>
  );
};

interface ModalFooterProps {
  onCancel: () => void;
  submitLabel?: string;
  isSubmitting?: boolean;
}

export const ModalFooter = ({ onCancel, submitLabel = "Simpan", isSubmitting = false }: ModalFooterProps) => (
  <div className="mt-6 flex justify-end space-x-3">
    <button
      type="button"
      onClick={onCancel}
      className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
    >
      Batal
    </button>
    <button
      type="submit"
      disabled={isSubmitting}
      className="rounded-md bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:bg-gray-400"
    >
      {submitLabel}
    </button>
  </div>
);
