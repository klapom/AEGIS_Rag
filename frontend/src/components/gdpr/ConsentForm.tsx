/**
 * ConsentForm Component
 * Sprint 98 Feature 98.3: GDPR Consent Manager UI
 *
 * Form for creating or editing GDPR consent records.
 * Includes legal basis selection, data category multi-select, and expiration date picker.
 */

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import type {
  GDPRConsent,
  ConsentFormData,
  LegalBasis,
  DataCategory,
} from '../../types/gdpr';
import { getLegalBasisText } from '../../types/gdpr';

interface ConsentFormProps {
  consent?: GDPRConsent; // If provided, edit mode; otherwise create mode
  onSubmit: (data: ConsentFormData) => void;
  onCancel: () => void;
}

const legalBasisOptions: LegalBasis[] = [
  'consent',
  'contract',
  'legal_obligation',
  'vital_interests',
  'public_task',
  'legitimate_interests',
];

const dataCategoryOptions: DataCategory[] = [
  'identifier',
  'contact',
  'financial',
  'health',
  'behavioral',
  'biometric',
  'location',
  'demographic',
  'professional',
  'other',
];

export function ConsentForm({ consent, onSubmit, onCancel }: ConsentFormProps) {
  const isEditMode = consent !== undefined;

  const [formData, setFormData] = useState<ConsentFormData>({
    userId: consent?.userId || '',
    purpose: consent?.purpose || '',
    legalBasis: consent?.legalBasis || 'consent',
    dataCategories: consent?.dataCategories || [],
    skillRestrictions: consent?.skillRestrictions || [],
    expiresAt: consent?.expiresAt || null,
  });

  const [skillInput, setSkillInput] = useState('');
  const [errors, setErrors] = useState<Partial<Record<keyof ConsentFormData, string>>>({});

  // Validate form
  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof ConsentFormData, string>> = {};

    if (!formData.userId.trim()) {
      newErrors.userId = 'User ID is required';
    }
    if (!formData.purpose.trim()) {
      newErrors.purpose = 'Purpose is required';
    }
    if (formData.dataCategories.length === 0) {
      newErrors.dataCategories = 'At least one data category is required';
    }
    if (
      formData.expiresAt &&
      new Date(formData.expiresAt) <= new Date()
    ) {
      newErrors.expiresAt = 'Expiration date must be in the future';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      onSubmit(formData);
    }
  };

  const handleDataCategoryToggle = (category: DataCategory) => {
    setFormData((prev) => ({
      ...prev,
      dataCategories: prev.dataCategories.includes(category)
        ? prev.dataCategories.filter((c) => c !== category)
        : [...prev.dataCategories, category],
    }));
  };

  const handleAddSkillRestriction = () => {
    if (skillInput.trim() && !formData.skillRestrictions.includes(skillInput.trim())) {
      setFormData((prev) => ({
        ...prev,
        skillRestrictions: [...prev.skillRestrictions, skillInput.trim()],
      }));
      setSkillInput('');
    }
  };

  const handleRemoveSkillRestriction = (skill: string) => {
    setFormData((prev) => ({
      ...prev,
      skillRestrictions: prev.skillRestrictions.filter((s) => s !== skill),
    }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            {isEditMode ? 'Edit Consent' : 'Create New Consent'}
          </h2>
          <button
            onClick={onCancel}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* User ID */}
          <div>
            <label
              htmlFor="userId"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              User ID *
            </label>
            <input
              id="userId"
              type="text"
              value={formData.userId}
              onChange={(e) => setFormData({ ...formData, userId: e.target.value })}
              disabled={isEditMode}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-700 disabled:cursor-not-allowed"
            />
            {errors.userId && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.userId}</p>
            )}
          </div>

          {/* Purpose */}
          <div>
            <label
              htmlFor="purpose"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Purpose *
            </label>
            <input
              id="purpose"
              type="text"
              placeholder="e.g., Customer Support, Marketing Communications"
              value={formData.purpose}
              onChange={(e) => setFormData({ ...formData, purpose: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
            />
            {errors.purpose && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.purpose}</p>
            )}
          </div>

          {/* Legal Basis */}
          <div>
            <label
              htmlFor="legalBasis"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Legal Basis (GDPR Article 6) *
            </label>
            <select
              id="legalBasis"
              value={formData.legalBasis}
              onChange={(e) =>
                setFormData({ ...formData, legalBasis: e.target.value as LegalBasis })
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
            >
              {legalBasisOptions.map((basis) => (
                <option key={basis} value={basis}>
                  {getLegalBasisText(basis)}
                </option>
              ))}
            </select>
          </div>

          {/* Data Categories */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Data Categories *
            </label>
            <div className="grid grid-cols-2 gap-2">
              {dataCategoryOptions.map((category) => (
                <label
                  key={category}
                  className="flex items-center gap-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={formData.dataCategories.includes(category)}
                    onChange={() => handleDataCategoryToggle(category)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-900 dark:text-gray-100 capitalize">
                    {category}
                  </span>
                </label>
              ))}
            </div>
            {errors.dataCategories && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                {errors.dataCategories}
              </p>
            )}
          </div>

          {/* Skill Restrictions */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Skill Restrictions (optional)
            </label>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
              Leave empty to allow all skills. Add specific skill names to restrict access.
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddSkillRestriction();
                  }
                }}
                placeholder="e.g., customer_support"
                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={handleAddSkillRestriction}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Add
              </button>
            </div>
            {formData.skillRestrictions.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {formData.skillRestrictions.map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm rounded"
                  >
                    {skill}
                    <button
                      type="button"
                      onClick={() => handleRemoveSkillRestriction(skill)}
                      className="text-gray-500 hover:text-red-600 dark:hover:text-red-400"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Expiration Date */}
          <div>
            <label
              htmlFor="expiresAt"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Expiration Date (optional)
            </label>
            <input
              id="expiresAt"
              type="date"
              value={
                formData.expiresAt
                  ? new Date(formData.expiresAt).toISOString().split('T')[0]
                  : ''
              }
              onChange={(e) =>
                setFormData({
                  ...formData,
                  expiresAt: e.target.value ? new Date(e.target.value).toISOString() : null,
                })
              }
              min={new Date().toISOString().split('T')[0]}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
            />
            {errors.expiresAt && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.expiresAt}</p>
            )}
            <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
              Leave empty for no expiration (consent remains valid indefinitely)
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              {isEditMode ? 'Update Consent' : 'Create Consent'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
