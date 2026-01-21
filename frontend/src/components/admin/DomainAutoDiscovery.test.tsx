/**
 * DomainAutoDiscovery Component Tests
 * Sprint 46 Feature 46.5: DomainAutoDiscovery Frontend Component
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { DomainAutoDiscovery, type DomainSuggestion } from './DomainAutoDiscovery';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('DomainAutoDiscovery', () => {
  const defaultProps = {
    onDomainSuggested: vi.fn(),
    onAccept: vi.fn(),
    onCancel: vi.fn(),
  };

  const mockSuggestion: DomainSuggestion = {
    title: 'omnitracker_docs',
    description: 'Documentation for OmniTracker IT service management system',
    confidence: 0.85,
    detected_topics: ['Python', 'FastAPI', 'Documentation'],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ============================================================================
  // Rendering Tests
  // ============================================================================

  describe('rendering', () => {
    it('should render the component with drop zone', () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      expect(screen.getByTestId('domain-auto-discovery')).toBeInTheDocument();
      expect(screen.getByTestId('domain-discovery-upload-area')).toBeInTheDocument();
    });

    it('should render description text', () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      expect(
        screen.getByText(/laden sie 1-3 beispieldokumente hoch/i)
      ).toBeInTheDocument();
    });

    it('should render file format instructions', () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      expect(screen.getByText(/unterstützt: txt, md, docx, html/i)).toBeInTheDocument();
      expect(screen.getByText(/max. 3 dateien, je 10 mb/i)).toBeInTheDocument();
    });

    it('should render cancel button', () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      expect(screen.getByTestId('cancel-button')).toBeInTheDocument();
    });

    it('should not render analyze button when no files are uploaded', () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      expect(screen.queryByTestId('domain-discovery-analyze-button')).not.toBeInTheDocument();
    });
  });

  // ============================================================================
  // File Upload Tests
  // ============================================================================

  describe('file upload', () => {
    it('should accept valid TXT file', async () => {
      const user = userEvent.setup();
      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');

      await user.upload(input, file);

      expect(screen.getByTestId('uploaded-file-test.txt')).toBeInTheDocument();
      expect(screen.getByText('test.txt')).toBeInTheDocument();
    });

    it('should accept valid MD file', async () => {
      const user = userEvent.setup();
      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['# Test'], 'readme.md', { type: 'text/markdown' });
      const input = screen.getByTestId('domain-discovery-file-input');

      await user.upload(input, file);

      expect(screen.getByTestId('uploaded-file-readme.md')).toBeInTheDocument();
    });

    it('should accept valid DOCX file', async () => {
      const user = userEvent.setup();
      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'document.docx', {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      });
      const input = screen.getByTestId('domain-discovery-file-input');

      await user.upload(input, file);

      expect(screen.getByTestId('uploaded-file-document.docx')).toBeInTheDocument();
    });

    it('should accept valid HTML file', async () => {
      const user = userEvent.setup();
      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['<html></html>'], 'page.html', { type: 'text/html' });
      const input = screen.getByTestId('domain-discovery-file-input');

      await user.upload(input, file);

      expect(screen.getByTestId('uploaded-file-page.html')).toBeInTheDocument();
    });

    it('should reject unsupported file format', async () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'image.png', { type: 'image/png' });
      const input = screen.getByTestId('domain-discovery-file-input') as HTMLInputElement;

      // Manually trigger file input change since userEvent may not handle all file types
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });
      fireEvent.change(input);

      await waitFor(() => {
        expect(screen.getByTestId('domain-discovery-error')).toBeInTheDocument();
      });
      expect(screen.getByText(/nicht unterstütztes format/i)).toBeInTheDocument();
    });

    it('should reject file exceeding size limit', async () => {
      const user = userEvent.setup();
      render(<DomainAutoDiscovery {...defaultProps} />);

      // Create a file larger than 10MB
      const largeContent = 'x'.repeat(11 * 1024 * 1024);
      const file = new File([largeContent], 'large.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');

      await user.upload(input, file);

      expect(screen.getByTestId('domain-discovery-error')).toBeInTheDocument();
      expect(screen.getByText(/datei zu groß/i)).toBeInTheDocument();
    });

    it('should reject more than 3 files', async () => {
      const user = userEvent.setup();
      render(<DomainAutoDiscovery {...defaultProps} />);

      const input = screen.getByTestId('domain-discovery-file-input');

      // Upload 3 files first
      await user.upload(input, [
        new File(['1'], 'file1.txt', { type: 'text/plain' }),
        new File(['2'], 'file2.txt', { type: 'text/plain' }),
        new File(['3'], 'file3.txt', { type: 'text/plain' }),
      ]);

      // Try to upload a 4th file
      await user.upload(input, new File(['4'], 'file4.txt', { type: 'text/plain' }));

      expect(screen.getByTestId('domain-discovery-error')).toBeInTheDocument();
      expect(screen.getByText(/maximal 3 dateien/i)).toBeInTheDocument();
    });

    it('should reject duplicate file names', async () => {
      const user = userEvent.setup();
      render(<DomainAutoDiscovery {...defaultProps} />);

      const input = screen.getByTestId('domain-discovery-file-input');

      // Upload first file
      await user.upload(input, new File(['content'], 'test.txt', { type: 'text/plain' }));

      // Try to upload same file again
      await user.upload(input, new File(['different'], 'test.txt', { type: 'text/plain' }));

      expect(screen.getByTestId('domain-discovery-error')).toBeInTheDocument();
      expect(screen.getByText(/datei bereits hochgeladen/i)).toBeInTheDocument();
    });

    it('should show analyze button after file upload', async () => {
      const user = userEvent.setup();
      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');

      await user.upload(input, file);

      expect(screen.getByTestId('domain-discovery-analyze-button')).toBeInTheDocument();
    });

    it('should remove file when remove button clicked', async () => {
      const user = userEvent.setup();
      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');

      await user.upload(input, file);
      expect(screen.getByTestId('uploaded-file-test.txt')).toBeInTheDocument();

      await user.click(screen.getByTestId('remove-file-test.txt'));
      expect(screen.queryByTestId('uploaded-file-test.txt')).not.toBeInTheDocument();
    });

    it('should display file size', async () => {
      const user = userEvent.setup();
      render(<DomainAutoDiscovery {...defaultProps} />);

      const content = 'test content here';
      const file = new File([content], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');

      await user.upload(input, file);

      // Should display file size (content is ~17 bytes)
      expect(screen.getByText(/\(\d+(\.\d+)?\s*(B|KB)\)/)).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Drag & Drop Tests
  // ============================================================================

  describe('drag and drop', () => {
    it('should highlight drop zone on drag over', () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      const dropZone = screen.getByTestId('domain-discovery-upload-area');

      fireEvent.dragOver(dropZone, {
        dataTransfer: { files: [] },
      });

      expect(dropZone).toHaveClass('border-blue-500', 'bg-blue-50');
    });

    it('should remove highlight on drag leave', () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      const dropZone = screen.getByTestId('domain-discovery-upload-area');

      fireEvent.dragOver(dropZone, {
        dataTransfer: { files: [] },
      });
      fireEvent.dragLeave(dropZone, {
        dataTransfer: { files: [] },
      });

      expect(dropZone).not.toHaveClass('border-blue-500');
    });

    it('should handle file drop', async () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      const dropZone = screen.getByTestId('domain-discovery-upload-area');
      const file = new File(['content'], 'dropped.txt', { type: 'text/plain' });

      fireEvent.drop(dropZone, {
        dataTransfer: {
          files: [file],
        },
      });

      await waitFor(() => {
        expect(screen.getByTestId('uploaded-file-dropped.txt')).toBeInTheDocument();
      });
    });
  });

  // ============================================================================
  // API Integration Tests
  // ============================================================================

  describe('API integration', () => {
    it('should call API on analyze button click', async () => {
      const user = userEvent.setup();

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuggestion,
      });

      render(<DomainAutoDiscovery {...defaultProps} />);

      // Upload a file first
      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');
      await user.upload(input, file);

      // Click analyze
      await user.click(screen.getByTestId('domain-discovery-analyze-button'));

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/admin/domains/discover'),
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
        })
      );
    });

    it('should show loading state during analysis', async () => {
      const user = userEvent.setup();

      // Create a promise that won't resolve immediately
      let resolvePromise: (value: unknown) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      mockFetch.mockReturnValueOnce(pendingPromise);

      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');
      await user.upload(input, file);

      await user.click(screen.getByTestId('domain-discovery-analyze-button'));

      expect(screen.getByText(/analysiere dokumente/i)).toBeInTheDocument();

      // Clean up
      resolvePromise!({
        ok: true,
        json: async () => mockSuggestion,
      });
    });

    it('should display suggestion after successful analysis', async () => {
      const user = userEvent.setup();

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuggestion,
      });

      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');
      await user.upload(input, file);

      await user.click(screen.getByTestId('domain-discovery-analyze-button'));

      await waitFor(() => {
        expect(screen.getByTestId('domain-discovery-suggestion')).toBeInTheDocument();
      });

      expect(screen.getByTestId('domain-discovery-suggestion-title')).toHaveTextContent('omnitracker_docs');
      expect(screen.getByTestId('domain-discovery-suggestion-description')).toHaveTextContent(
        'Documentation for OmniTracker'
      );
    });

    it('should call onDomainSuggested callback after analysis', async () => {
      const user = userEvent.setup();
      const onDomainSuggested = vi.fn();

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuggestion,
      });

      render(<DomainAutoDiscovery {...defaultProps} onDomainSuggested={onDomainSuggested} />);

      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');
      await user.upload(input, file);

      await user.click(screen.getByTestId('domain-discovery-analyze-button'));

      await waitFor(() => {
        expect(onDomainSuggested).toHaveBeenCalledWith(mockSuggestion);
      });
    });

    it('should show error on API failure', async () => {
      const user = userEvent.setup();

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Internal Server Error',
      });

      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');
      await user.upload(input, file);

      await user.click(screen.getByTestId('domain-discovery-analyze-button'));

      await waitFor(() => {
        expect(screen.getByTestId('domain-discovery-error')).toBeInTheDocument();
      });

      expect(screen.getByText(/http 500/i)).toBeInTheDocument();
    });

    it('should show error on network failure', async () => {
      const user = userEvent.setup();

      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');
      await user.upload(input, file);

      await user.click(screen.getByTestId('domain-discovery-analyze-button'));

      await waitFor(() => {
        expect(screen.getByTestId('domain-discovery-error')).toBeInTheDocument();
      });

      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Suggestion Display Tests
  // ============================================================================

  describe('suggestion display', () => {
    const setupWithSuggestion = async () => {
      const user = userEvent.setup();

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuggestion,
      });

      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');
      await user.upload(input, file);
      await user.click(screen.getByTestId('domain-discovery-analyze-button'));

      await waitFor(() => {
        expect(screen.getByTestId('domain-discovery-suggestion')).toBeInTheDocument();
      });

      return user;
    };

    it('should display confidence indicator', async () => {
      await setupWithSuggestion();

      expect(screen.getByTestId('confidence-indicator')).toBeInTheDocument();
      expect(screen.getByText(/hoch \(85%\)/i)).toBeInTheDocument();
    });

    it('should display detected topics', async () => {
      await setupWithSuggestion();

      expect(screen.getByTestId('topic-0')).toHaveTextContent('Python');
      expect(screen.getByTestId('topic-1')).toHaveTextContent('FastAPI');
      expect(screen.getByTestId('topic-2')).toHaveTextContent('Documentation');
    });

    it('should show edit and accept buttons', async () => {
      await setupWithSuggestion();

      expect(screen.getByTestId('edit-button')).toBeInTheDocument();
      expect(screen.getByTestId('domain-discovery-accept-button')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Editing Tests
  // ============================================================================

  describe('editing', () => {
    const setupWithSuggestion = async () => {
      const user = userEvent.setup();

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuggestion,
      });

      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');
      await user.upload(input, file);
      await user.click(screen.getByTestId('domain-discovery-analyze-button'));

      await waitFor(() => {
        expect(screen.getByTestId('domain-discovery-suggestion')).toBeInTheDocument();
      });

      return user;
    };

    it('should switch to edit mode when edit button clicked', async () => {
      const user = await setupWithSuggestion();

      await user.click(screen.getByTestId('edit-button'));

      expect(screen.getByTestId('edit-title-input')).toBeInTheDocument();
      expect(screen.getByTestId('edit-description-input')).toBeInTheDocument();
    });

    it('should populate edit fields with suggestion values', async () => {
      const user = await setupWithSuggestion();

      await user.click(screen.getByTestId('edit-button'));

      expect(screen.getByTestId('edit-title-input')).toHaveValue('omnitracker_docs');
      expect(screen.getByTestId('edit-description-input')).toHaveValue(
        mockSuggestion.description
      );
    });

    it('should allow editing title', async () => {
      const user = await setupWithSuggestion();

      await user.click(screen.getByTestId('edit-button'));
      const titleInput = screen.getByTestId('edit-title-input');

      await user.clear(titleInput);
      await user.type(titleInput, 'new_domain');

      expect(titleInput).toHaveValue('new_domain');
    });

    it('should sanitize title input (lowercase, underscores)', async () => {
      const user = await setupWithSuggestion();

      await user.click(screen.getByTestId('edit-button'));
      const titleInput = screen.getByTestId('edit-title-input');

      await user.clear(titleInput);
      await user.type(titleInput, 'My Domain Name');

      // Should be sanitized to lowercase with underscores
      expect(titleInput).toHaveValue('my_domain_name');
    });

    it('should allow editing description', async () => {
      const user = await setupWithSuggestion();

      await user.click(screen.getByTestId('edit-button'));
      const descInput = screen.getByTestId('edit-description-input');

      await user.clear(descInput);
      await user.type(descInput, 'New description');

      expect(descInput).toHaveValue('New description');
    });

    it('should show cancel edit button in edit mode', async () => {
      const user = await setupWithSuggestion();

      await user.click(screen.getByTestId('edit-button'));

      expect(screen.getByTestId('cancel-edit-button')).toBeInTheDocument();
      expect(screen.queryByTestId('edit-button')).not.toBeInTheDocument();
    });

    it('should revert changes when cancel edit clicked', async () => {
      const user = await setupWithSuggestion();

      await user.click(screen.getByTestId('edit-button'));
      const titleInput = screen.getByTestId('edit-title-input');

      await user.clear(titleInput);
      await user.type(titleInput, 'changed');

      await user.click(screen.getByTestId('cancel-edit-button'));

      // Should show original values in non-edit mode
      expect(screen.getByTestId('domain-discovery-suggestion-title')).toHaveTextContent('omnitracker_docs');
    });
  });

  // ============================================================================
  // Accept & Cancel Tests
  // ============================================================================

  describe('accept and cancel', () => {
    const setupWithSuggestion = async () => {
      const user = userEvent.setup();

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSuggestion,
      });

      const onAccept = vi.fn();
      render(<DomainAutoDiscovery {...defaultProps} onAccept={onAccept} />);

      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');
      await user.upload(input, file);
      await user.click(screen.getByTestId('domain-discovery-analyze-button'));

      await waitFor(() => {
        expect(screen.getByTestId('domain-discovery-suggestion')).toBeInTheDocument();
      });

      return { user, onAccept };
    };

    it('should call onAccept with suggestion values when accept clicked', async () => {
      const { user, onAccept } = await setupWithSuggestion();

      await user.click(screen.getByTestId('domain-discovery-accept-button'));

      expect(onAccept).toHaveBeenCalledWith('omnitracker_docs', mockSuggestion.description);
    });

    it('should call onAccept with edited values when accept clicked after edit', async () => {
      const { user, onAccept } = await setupWithSuggestion();

      await user.click(screen.getByTestId('edit-button'));

      const titleInput = screen.getByTestId('edit-title-input');
      await user.clear(titleInput);
      await user.type(titleInput, 'custom_domain');

      const descInput = screen.getByTestId('edit-description-input');
      await user.clear(descInput);
      await user.type(descInput, 'Custom description');

      await user.click(screen.getByTestId('domain-discovery-accept-button'));

      expect(onAccept).toHaveBeenCalledWith('custom_domain', 'Custom description');
    });

    it('should call onCancel when cancel button clicked', async () => {
      const user = userEvent.setup();
      const onCancel = vi.fn();

      render(<DomainAutoDiscovery {...defaultProps} onCancel={onCancel} />);

      await user.click(screen.getByTestId('cancel-button'));

      expect(onCancel).toHaveBeenCalledTimes(1);
    });
  });

  // ============================================================================
  // Confidence Indicator Tests
  // ============================================================================

  describe('confidence indicator', () => {
    const setupWithConfidence = async (confidence: number) => {
      const user = userEvent.setup();

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockSuggestion, confidence }),
      });

      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');
      await user.upload(input, file);
      await user.click(screen.getByTestId('domain-discovery-analyze-button'));

      await waitFor(() => {
        expect(screen.getByTestId('domain-discovery-suggestion')).toBeInTheDocument();
      });
    };

    it('should show "Hoch" for confidence > 0.8', async () => {
      await setupWithConfidence(0.9);

      expect(screen.getByText(/hoch \(90%\)/i)).toBeInTheDocument();
    });

    it('should show "Mittel" for confidence 0.5-0.8', async () => {
      await setupWithConfidence(0.65);

      expect(screen.getByText(/mittel \(65%\)/i)).toBeInTheDocument();
    });

    it('should show "Niedrig" for confidence < 0.5', async () => {
      await setupWithConfidence(0.3);

      expect(screen.getByText(/niedrig \(30%\)/i)).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Accessibility Tests
  // ============================================================================

  describe('accessibility', () => {
    it('should have accessible drop zone', () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      const dropZone = screen.getByTestId('domain-discovery-upload-area');
      expect(dropZone).toHaveAttribute('role', 'button');
      expect(dropZone).toHaveAttribute('tabIndex', '0');
      expect(dropZone).toHaveAttribute('aria-label', 'Dateien hochladen');
    });

    it('should have accessible file input', () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      const input = screen.getByTestId('domain-discovery-file-input');
      expect(input).toHaveAttribute('aria-label', 'Datei auswählen');
    });

    it('should have accessible remove buttons', async () => {
      const user = userEvent.setup();
      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const input = screen.getByTestId('domain-discovery-file-input');
      await user.upload(input, file);

      const removeButton = screen.getByTestId('remove-file-test.txt');
      expect(removeButton).toHaveAttribute('aria-label', 'test.txt entfernen');
    });

    it('should activate drop zone on keyboard (Enter)', async () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      const dropZone = screen.getByTestId('domain-discovery-upload-area');
      const fileInput = screen.getByTestId('domain-discovery-file-input');

      // Spy on click event
      const clickSpy = vi.spyOn(fileInput, 'click');

      fireEvent.keyDown(dropZone, { key: 'Enter' });

      expect(clickSpy).toHaveBeenCalled();
    });

    it('should activate drop zone on keyboard (Space)', async () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      const dropZone = screen.getByTestId('domain-discovery-upload-area');
      const fileInput = screen.getByTestId('domain-discovery-file-input');

      const clickSpy = vi.spyOn(fileInput, 'click');

      fireEvent.keyDown(dropZone, { key: ' ' });

      expect(clickSpy).toHaveBeenCalled();
    });

    it('should have error alerts with role="alert"', async () => {
      render(<DomainAutoDiscovery {...defaultProps} />);

      const file = new File(['content'], 'test.exe', { type: 'application/x-msdownload' });
      const input = screen.getByTestId('domain-discovery-file-input') as HTMLInputElement;

      // Manually trigger file input change since userEvent may not handle all file types
      Object.defineProperty(input, 'files', {
        value: [file],
        writable: false,
      });
      fireEvent.change(input);

      await waitFor(() => {
        expect(screen.getByTestId('domain-discovery-error')).toBeInTheDocument();
      });

      const error = screen.getByTestId('domain-discovery-error');
      expect(error).toHaveAttribute('role', 'alert');
    });
  });
});
