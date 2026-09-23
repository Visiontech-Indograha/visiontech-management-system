import React, { useId } from "react";

interface FieldWrapperProps {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}

const FieldWrapper = ({ label, htmlFor, children }: FieldWrapperProps) => (
  <div>
    <label htmlFor={htmlFor} className="block text-sm font-medium text-gray-700">
      {label}
    </label>
    <div className="mt-1">{children}</div>
  </div>
);

const fieldClassName =
  "block w-full rounded-md border border-gray-300 p-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export const Input = ({ label, id, className = "", ...rest }: InputProps) => {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <FieldWrapper label={label} htmlFor={inputId}>
      <input id={inputId} className={`${fieldClassName} ${className}`} {...rest} />
    </FieldWrapper>
  );
};

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
}

export const TextArea = ({ label, id, className = "", ...rest }: TextAreaProps) => {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <FieldWrapper label={label} htmlFor={inputId}>
      <textarea id={inputId} className={`${fieldClassName} ${className}`} {...rest} />
    </FieldWrapper>
  );
};

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
}

export const Select = ({ label, id, className = "", children, ...rest }: SelectProps) => {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <FieldWrapper label={label} htmlFor={inputId}>
      <select id={inputId} className={`${fieldClassName} bg-white ${className}`} {...rest}>
        {children}
      </select>
    </FieldWrapper>
  );
};
