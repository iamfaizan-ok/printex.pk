import React, { useRef } from 'react';

export interface FilePickerProps {
  onFilesSelected: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
  children: (openPicker: () => void) => React.ReactNode;
}

export const FilePicker: React.FC<FilePickerProps> = ({
  onFilesSelected,
  accept = '.pdf,application/pdf,image/*,.png,.jpg,.jpeg,.webp,.svg,.bmp',
  multiple = true,
  disabled = false,
  children,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleOpen = () => {
    if (disabled) return;
    if (inputRef.current) {
      inputRef.current.value = ''; // Reset input to allow selecting the same file again if replaced
      inputRef.current.click();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const fileList = Array.from(e.target.files);
      onFilesSelected(fileList);
    }
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        onChange={handleChange}
        className="hidden"
        aria-hidden="true"
        tabIndex={-1}
      />
      {children(handleOpen)}
    </>
  );
};
