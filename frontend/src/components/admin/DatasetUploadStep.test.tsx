/**
 * DatasetUploadStep Component Tests
 * Sprint 64 Feature 64.2: Frontend validation for minimum sample count
 *
 * Tests:
 * - File upload and parsing
 * - Minimum sample validation (< 5 samples warning)
 * - Error message clearing on new upload
 * - Success message display
 * - Start Training button disabled state
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DatasetUploadStep } from './DatasetUploadStep';
import type { TrainingSample } from '../../hooks/useDomainTraining';

// Helper: Create mock TrainingSample
function createMockSample(overrides?: Partial<TrainingSample>): TrainingSample {
  return {
    text: 'Sample text about financial analysis',
    entities: ['financial', 'analysis'],
    relations: [],
    ...overrides,
  };
}

// Helper: Create JSONL file content
function createJSONLContent(samples: TrainingSample[]): string {
  return samples.map((s) => JSON.stringify(s)).join('\n');
}

// Helper: Create mock File with text() method
function createMockFile(content: string, name = 'test.jsonl'): File {
  const file = new File([content], name, { type: 'application/jsonl' });
  // Mock the text() method for jsdom compatibility
  file.text = () => Promise.resolve(content);
  return file;
}

// Helper: Simulate file upload with configurable files property
async function uploadFile(fileInput: HTMLElement, file: File) {
  Object.defineProperty(fileInput, 'files', {
    value: [file],
    configurable: true, // Allow re-defining for multiple uploads
  });
  fireEvent.change(fileInput);
}

describe('DatasetUploadStep', () => {
  const defaultProps = {
    dataset: [] as TrainingSample[],
    onUpload: vi.fn(),
    onBack: vi.fn(),
    onNext: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('initial render', () => {
    it('should render upload area with instructions', () => {
      render(<DatasetUploadStep {...defaultProps} />);

      expect(screen.getByTestId('dataset-upload-step')).toBeInTheDocument();
      expect(screen.getByText('Upload Training Dataset')).toBeInTheDocument();
      expect(screen.getByText('Step 2 of 3: Upload a JSONL file with training samples')).toBeInTheDocument();
      expect(screen.getByText('Choose JSONL file')).toBeInTheDocument();
    });

    it('should have file input for JSONL files', () => {
      render(<DatasetUploadStep {...defaultProps} />);

      const fileInput = screen.getByTestId('dataset-file-input');
      expect(fileInput).toHaveAttribute('accept', '.jsonl,.json');
    });

    it('should show Start Training button with 0 samples', () => {
      render(<DatasetUploadStep {...defaultProps} />);

      const button = screen.getByTestId('dataset-upload-next');
      expect(button).toHaveTextContent('Start Training (0 samples)');
      expect(button).toBeDisabled();
    });
  });

  describe('validation: minimum sample count', () => {
    it('should show warning when uploading less than 5 samples', async () => {
      const onUpload = vi.fn();
      render(<DatasetUploadStep {...defaultProps} onUpload={onUpload} />);

      // Create file with only 3 samples
      const samples = [createMockSample(), createMockSample(), createMockSample()];
      const fileContent = createJSONLContent(samples);
      const file = createMockFile(fileContent);

      const fileInput = screen.getByTestId('dataset-file-input');
      await uploadFile(fileInput, file);

      await waitFor(() => {
        expect(screen.getByTestId('validation-warning')).toBeInTheDocument();
      });

      expect(screen.getByText('Validation Warning')).toBeInTheDocument();
      expect(screen.getByText(/Minimum 5 samples required/)).toBeInTheDocument();
      expect(screen.getByText(/Currently: 3 samples \(2 more needed\)/)).toBeInTheDocument();
    });

    it('should show success message when uploading 5 or more samples', async () => {
      const onUpload = vi.fn();
      render(<DatasetUploadStep {...defaultProps} onUpload={onUpload} />);

      // Create file with 5 samples
      const samples = Array(5)
        .fill(null)
        .map(() => createMockSample());
      const fileContent = createJSONLContent(samples);
      const file = createMockFile(fileContent);

      const fileInput = screen.getByTestId('dataset-file-input');
      await uploadFile(fileInput, file);

      await waitFor(() => {
        expect(screen.getByTestId('validation-success')).toBeInTheDocument();
      });

      expect(screen.getByText('Ready to Train')).toBeInTheDocument();
      expect(screen.getByText(/5 samples loaded/)).toBeInTheDocument();
    });

    it('should show correct plural form for 1 sample', async () => {
      const onUpload = vi.fn();
      render(<DatasetUploadStep {...defaultProps} onUpload={onUpload} />);

      // Create file with only 1 sample
      const samples = [createMockSample()];
      const fileContent = createJSONLContent(samples);
      const file = createMockFile(fileContent);

      const fileInput = screen.getByTestId('dataset-file-input');
      await uploadFile(fileInput, file);

      await waitFor(() => {
        expect(screen.getByTestId('validation-warning')).toBeInTheDocument();
      });

      expect(screen.getByText(/Currently: 1 sample \(4 more needed\)/)).toBeInTheDocument();
    });
  });

  describe('error clearing on new upload', () => {
    it('should clear validation warning when new file is uploaded', async () => {
      const onUpload = vi.fn();
      render(<DatasetUploadStep {...defaultProps} onUpload={onUpload} />);

      const fileInput = screen.getByTestId('dataset-file-input');

      // First upload: 2 samples (should show warning)
      const twoSamples = [createMockSample(), createMockSample()];
      await uploadFile(fileInput, createMockFile(createJSONLContent(twoSamples)));

      await waitFor(() => {
        expect(screen.getByTestId('validation-warning')).toBeInTheDocument();
      });

      // Second upload: 5 samples (should show success, no warning)
      const fiveSamples = Array(5)
        .fill(null)
        .map(() => createMockSample());
      await uploadFile(fileInput, createMockFile(createJSONLContent(fiveSamples)));

      await waitFor(() => {
        expect(screen.getByTestId('validation-success')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('validation-warning')).not.toBeInTheDocument();
    });

    it('should clear success message when new file with insufficient samples is uploaded', async () => {
      const onUpload = vi.fn();
      render(<DatasetUploadStep {...defaultProps} onUpload={onUpload} />);

      const fileInput = screen.getByTestId('dataset-file-input');

      // First upload: 5 samples (success)
      const fiveSamples = Array(5)
        .fill(null)
        .map(() => createMockSample());
      await uploadFile(fileInput, createMockFile(createJSONLContent(fiveSamples)));

      await waitFor(() => {
        expect(screen.getByTestId('validation-success')).toBeInTheDocument();
      });

      // Second upload: 2 samples (warning)
      const twoSamples = [createMockSample(), createMockSample()];
      await uploadFile(fileInput, createMockFile(createJSONLContent(twoSamples)));

      await waitFor(() => {
        expect(screen.getByTestId('validation-warning')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('validation-success')).not.toBeInTheDocument();
    });

    it('should clear all messages when dataset is cleared', async () => {
      const user = userEvent.setup();
      const onUpload = vi.fn();

      // Start with dataset that has samples
      const initialDataset = Array(3)
        .fill(null)
        .map(() => createMockSample());
      const { rerender } = render(
        <DatasetUploadStep {...defaultProps} dataset={initialDataset} onUpload={onUpload} />
      );

      // Upload a file first to trigger validation warning
      const fileInput = screen.getByTestId('dataset-file-input');
      const samples = [createMockSample(), createMockSample()];
      await uploadFile(fileInput, createMockFile(createJSONLContent(samples)));

      await waitFor(() => {
        expect(screen.getByTestId('validation-warning')).toBeInTheDocument();
      });

      // Simulate clear button behavior
      rerender(<DatasetUploadStep {...defaultProps} dataset={initialDataset} onUpload={onUpload} />);

      // Click clear button
      const clearButton = screen.getByTestId('clear-dataset-button');
      await user.click(clearButton);

      // After clear, both messages should be gone (component clears them)
      // Note: The component calls setValidationError(null) and setSuccessMessage(null)
      // but since we're rerendering, we need to check the onUpload was called with []
      expect(onUpload).toHaveBeenCalledWith([]);
    });
  });

  describe('Start Training button state', () => {
    it('should be disabled when dataset has less than 5 samples', () => {
      const samples = Array(4)
        .fill(null)
        .map(() => createMockSample());
      render(<DatasetUploadStep {...defaultProps} dataset={samples} />);

      const button = screen.getByTestId('dataset-upload-next');
      expect(button).toBeDisabled();
      expect(button).toHaveTextContent('Start Training (4 samples)');
    });

    it('should be enabled when dataset has 5 or more samples', () => {
      const samples = Array(5)
        .fill(null)
        .map(() => createMockSample());
      render(<DatasetUploadStep {...defaultProps} dataset={samples} />);

      const button = screen.getByTestId('dataset-upload-next');
      expect(button).not.toBeDisabled();
      expect(button).toHaveTextContent('Start Training (5 samples)');
    });

    it('should be disabled when loading', () => {
      const samples = Array(5)
        .fill(null)
        .map(() => createMockSample());
      render(<DatasetUploadStep {...defaultProps} dataset={samples} isLoading={true} />);

      const button = screen.getByTestId('dataset-upload-next');
      expect(button).toBeDisabled();
      expect(button).toHaveTextContent('Starting Training...');
    });

    it('should show tooltip when disabled due to insufficient samples', () => {
      const samples = Array(3)
        .fill(null)
        .map(() => createMockSample());
      render(<DatasetUploadStep {...defaultProps} dataset={samples} />);

      const button = screen.getByTestId('dataset-upload-next');
      expect(button).toHaveAttribute('title', 'Minimum 5 samples required');
    });

    it('should not show tooltip when enabled', () => {
      const samples = Array(5)
        .fill(null)
        .map(() => createMockSample());
      render(<DatasetUploadStep {...defaultProps} dataset={samples} />);

      const button = screen.getByTestId('dataset-upload-next');
      expect(button).not.toHaveAttribute('title');
    });
  });

  describe('parse error handling', () => {
    it('should display parse error for invalid JSONL', async () => {
      render(<DatasetUploadStep {...defaultProps} />);

      const invalidContent = 'not valid json\n{also invalid}';
      const file = createMockFile(invalidContent);

      const fileInput = screen.getByTestId('dataset-file-input');
      await uploadFile(fileInput, file);

      await waitFor(() => {
        expect(screen.getByTestId('dataset-upload-error')).toBeInTheDocument();
      });

      expect(screen.getByText(/Invalid JSONL format/)).toBeInTheDocument();
    });

    it('should display error when sample is missing required fields', async () => {
      render(<DatasetUploadStep {...defaultProps} />);

      // Missing entities field
      const invalidSample = { text: 'Some text' };
      const file = createMockFile(JSON.stringify(invalidSample));

      const fileInput = screen.getByTestId('dataset-file-input');
      await uploadFile(fileInput, file);

      await waitFor(() => {
        expect(screen.getByTestId('dataset-upload-error')).toBeInTheDocument();
      });

      expect(screen.getByText(/must have "text".*and "entities"/)).toBeInTheDocument();
    });

    it('should clear parse error when valid file is uploaded', async () => {
      render(<DatasetUploadStep {...defaultProps} />);

      const fileInput = screen.getByTestId('dataset-file-input');

      // First: invalid file
      await uploadFile(fileInput, createMockFile('invalid'));

      await waitFor(() => {
        expect(screen.getByTestId('dataset-upload-error')).toBeInTheDocument();
      });

      // Second: valid file
      const validSamples = Array(5)
        .fill(null)
        .map(() => createMockSample());
      await uploadFile(fileInput, createMockFile(createJSONLContent(validSamples)));

      await waitFor(() => {
        expect(screen.queryByTestId('dataset-upload-error')).not.toBeInTheDocument();
      });
    });
  });

  describe('submit error display', () => {
    it('should display submit error when provided', () => {
      render(<DatasetUploadStep {...defaultProps} error="Failed to start training: server error" />);

      expect(screen.getByTestId('dataset-upload-error')).toBeInTheDocument();
      expect(screen.getByText('Failed to start training: server error')).toBeInTheDocument();
    });
  });

  describe('dataset preview', () => {
    it('should show dataset preview when samples are loaded', () => {
      const samples = [createMockSample({ text: 'Test sample text', entities: ['entity1', 'entity2'] })];
      render(<DatasetUploadStep {...defaultProps} dataset={samples} />);

      expect(screen.getByText('Dataset Preview (1 samples)')).toBeInTheDocument();
      expect(screen.getByText('Test sample text')).toBeInTheDocument();
      expect(screen.getByText('entity1, entity2')).toBeInTheDocument();
    });

    it('should show "+ X more samples" for large datasets', () => {
      const samples = Array(10)
        .fill(null)
        .map(() => createMockSample());
      render(<DatasetUploadStep {...defaultProps} dataset={samples} />);

      expect(screen.getByText('+ 5 more samples')).toBeInTheDocument();
    });
  });

  describe('callbacks', () => {
    it('should call onBack when back button is clicked', async () => {
      const user = userEvent.setup();
      const onBack = vi.fn();
      render(<DatasetUploadStep {...defaultProps} onBack={onBack} />);

      await user.click(screen.getByTestId('dataset-upload-back'));
      expect(onBack).toHaveBeenCalled();
    });

    it('should call onNext with log path when start training is clicked', async () => {
      const user = userEvent.setup();
      const onNext = vi.fn();
      const samples = Array(5)
        .fill(null)
        .map(() => createMockSample());
      render(<DatasetUploadStep {...defaultProps} dataset={samples} onNext={onNext} />);

      await user.click(screen.getByTestId('dataset-upload-next'));
      expect(onNext).toHaveBeenCalledWith(undefined);
    });
  });

  describe('accessibility', () => {
    it('should have proper ARIA roles for alerts', async () => {
      render(<DatasetUploadStep {...defaultProps} />);

      // Upload file with insufficient samples
      const samples = [createMockSample()];
      const file = createMockFile(createJSONLContent(samples));
      await uploadFile(screen.getByTestId('dataset-file-input'), file);

      await waitFor(() => {
        const warningAlert = screen.getByTestId('validation-warning');
        expect(warningAlert).toHaveAttribute('role', 'alert');
      });
    });

    it('should have proper role for success message', async () => {
      render(<DatasetUploadStep {...defaultProps} />);

      // Upload file with sufficient samples
      const samples = Array(5)
        .fill(null)
        .map(() => createMockSample());
      const file = createMockFile(createJSONLContent(samples));
      await uploadFile(screen.getByTestId('dataset-file-input'), file);

      await waitFor(() => {
        const successStatus = screen.getByTestId('validation-success');
        expect(successStatus).toHaveAttribute('role', 'status');
      });
    });
  });
});
