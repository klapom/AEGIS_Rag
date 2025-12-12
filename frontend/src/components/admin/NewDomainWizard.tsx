/**
 * NewDomainWizard Component
 * Sprint 45 Feature 45.4: Domain Training Admin UI
 *
 * 3-step wizard for creating and training a new domain
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

  const createDomain = useCreateDomain();
  const startTraining = useStartTraining();
  const { data: models } = useAvailableModels();

  const handleStartTraining = async () => {
    try {
      // Create domain
      await createDomain.mutateAsync({
        name: config.name,
        description: config.description,
        llm_model: config.llm_model || undefined,
      });

      // Start training
      await startTraining.mutateAsync({
        domain: config.name,
        dataset,
      });

      // Move to progress step
      setStep(3);
    } catch (error) {
      console.error('Failed to start training:', error);
      // Error is handled by the hooks, stay on current step
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
          />
        )}
        {step === 3 && <TrainingProgressStep domainName={config.name} onComplete={onClose} />}
      </div>
    </div>
  );
}
