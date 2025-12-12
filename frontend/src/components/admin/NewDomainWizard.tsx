/**
 * NewDomainWizard Component
 * Sprint 45 Feature 45.4, 45.13: Domain Training Admin UI with SSE and JSONL Export
 *
 * 3-step wizard for creating and training a new domain
 * Feature 45.13: SSE live streaming and optional JSONL log export
 */

import { useState } from 'react';
import {
  useCreateDomain,
  useStartTraining,
  useAvailableModels,
  type TrainingSample,
} from '../../hooks/useDomainTraining';
import { DomainConfigStep } from './DomainConfigStep';
import { DatasetUploadStep } from './DatasetUploadStep';
import { TrainingProgressStep } from './TrainingProgressStep';

interface NewDomainWizardProps {
  onClose: () => void;
}

export function NewDomainWizard({ onClose }: NewDomainWizardProps) {
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState({
    name: '',
    description: '',
    llm_model: 'qwen3:32b',
  });
  const [dataset, setDataset] = useState<TrainingSample[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [trainingRunId, setTrainingRunId] = useState<string | null>(null);

  const createDomain = useCreateDomain();
  const startTraining = useStartTraining();
  const { data: models } = useAvailableModels();

  const handleStartTraining = async (logPath?: string) => {
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      // Create domain
      await createDomain.mutateAsync({
        name: config.name,
        description: config.description,
        llm_model: config.llm_model || undefined,
      });

      // Start training with optional log path (Feature 45.13)
      const response = await startTraining.mutateAsync({
        domain: config.name,
        dataset,
        log_path: logPath,
      });

      // Store training_run_id for SSE streaming
      setTrainingRunId(response.training_run_id);

      // Move to progress step
      setStep(3);
    } catch (error) {
      console.error('Failed to start training:', error);
      setSubmitError(error instanceof Error ? error.message : 'Failed to start training');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      data-testid="new-domain-wizard"
    >
      <div className="bg-white rounded-lg w-[800px] max-h-[90vh] overflow-auto p-6">
        {step === 1 && (
          <DomainConfigStep
            config={config}
            models={models}
            onChange={setConfig}
            onNext={() => setStep(2)}
            onCancel={onClose}
          />
        )}
        {step === 2 && (
          <DatasetUploadStep
            dataset={dataset}
            onUpload={setDataset}
            onBack={() => setStep(1)}
            onNext={handleStartTraining}
            isLoading={isSubmitting}
            error={submitError}
          />
        )}
        {step === 3 && (
          <TrainingProgressStep
            domainName={config.name}
            trainingRunId={trainingRunId}
            onComplete={onClose}
          />
        )}
      </div>
    </div>
  );
}
