import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FileList } from '../src/components/upload/FileList';
import { EmptyOrderState } from '../src/components/order/EmptyOrderState';
import { PrintFile } from '../src/types/printFile';
import { DEFAULT_PRINT_SETTINGS } from '../src/config/printDefaults';
import { MemoryRouter } from 'react-router-dom';

describe('Upload and File Management Workflow Components', () => {
  it('renders EmptyOrderState with custom title and action button', () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <EmptyOrderState
          title="No documents uploaded"
          description="Please upload a PDF file to begin."
          actionText="Select Files"
          actionHref="/upload"
        />
      </MemoryRouter>
    );

    expect(screen.getByText('No documents uploaded')).toBeInTheDocument();
    expect(screen.getByText('Select Files')).toBeInTheDocument();
  });

  it('renders FileList with uploaded documents and page count badges', () => {
    const mockFiles: PrintFile[] = [
      {
        fileId: 'file_1',
        originalFileName: 'thesis_final.pdf',
        fileSize: 1024 * 500,
        pageCount: 14,
        processingStatus: 'ready',
        printSettings: { ...DEFAULT_PRINT_SETTINGS },
        uploadedAt: new Date().toISOString(),
      },
    ];

    const handleRemove = vi.fn();
    const handleReplace = vi.fn();
    const handleMoveUp = vi.fn();
    const handleMoveDown = vi.fn();
    const handleClearAll = vi.fn();

    render(
      <FileList
        files={mockFiles}
        onRemove={handleRemove}
        onReplace={handleReplace}
        onMoveUp={handleMoveUp}
        onMoveDown={handleMoveDown}
        onClearAll={handleClearAll}
      />
    );

    expect(screen.getByText('thesis_final.pdf')).toBeInTheDocument();
    expect(screen.getByText('14 pages')).toBeInTheDocument();
    expect(screen.getByText('Clear All')).toBeInTheDocument();
  });
});
