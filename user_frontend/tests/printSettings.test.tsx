import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CopiesInput } from '../src/components/printing/CopiesInput';
import { PaperSizeSelect } from '../src/components/printing/PaperSizeSelect';
import { PrintSettingsForm } from '../src/components/printing/PrintSettingsForm';
import { PrintFile } from '../src/types/printFile';
import { DEFAULT_PRINT_SETTINGS } from '../src/config/printDefaults';

describe('Print Settings Components', () => {
  it('CopiesInput updates value when increment and decrement buttons are clicked', () => {
    const handleChange = vi.fn();
    render(<CopiesInput value={3} onChange={handleChange} min={1} max={50} />);

    const decBtn = screen.getByTitle('Decrease copies');
    const incBtn = screen.getByTitle('Increase copies');

    fireEvent.click(decBtn);
    expect(handleChange).toHaveBeenCalledWith(2);

    fireEvent.click(incBtn);
    expect(handleChange).toHaveBeenCalledWith(4);
  });

  it('PaperSizeSelect renders A4, A3, Letter, Legal buttons and triggers onChange', () => {
    const handleChange = vi.fn();
    render(<PaperSizeSelect value="A4" onChange={handleChange} />);

    expect(screen.getByText('A4')).toBeInTheDocument();
    expect(screen.getByText('A3')).toBeInTheDocument();
    expect(screen.getByText('Letter')).toBeInTheDocument();
    expect(screen.getByText('Legal')).toBeInTheDocument();

    fireEvent.click(screen.getByText('A3'));
    expect(handleChange).toHaveBeenCalledWith('A3');
  });

  it('PrintSettingsForm renders all setting controls for a specific document', () => {
    const mockFile: PrintFile = {
      fileId: 'doc_1',
      originalFileName: 'contract.pdf',
      fileSize: 1024 * 50,
      pageCount: 5,
      processingStatus: 'ready',
      printSettings: { ...DEFAULT_PRINT_SETTINGS, copies: 2 },
      uploadedAt: new Date().toISOString(),
    };

    const handleUpdate = vi.fn();
    render(<PrintSettingsForm file={mockFile} onUpdateSettings={handleUpdate} />);

    expect(screen.getByText('contract.pdf')).toBeInTheDocument();
    expect(screen.getByText(/Number of Copies/i)).toBeInTheDocument();
    expect(screen.getByText(/Paper Size/i)).toBeInTheDocument();
    expect(screen.getByText(/Color Mode/i)).toBeInTheDocument();
    expect(screen.getByText(/Sides & Duplex/i)).toBeInTheDocument();
  });
});
