interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

/** Input pencarian bergaya konsisten — dipasangkan dengan `useDebouncedValue` di pemanggil. */
export const SearchBar = ({ value, onChange, placeholder = "Cari..." }: SearchBarProps) => (
  <div className="max-w-md">
    <input
      type="text"
      placeholder={placeholder}
      className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-4 py-2 border"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  </div>
);
