/**
 * SkillMdEditor Page Component
 * Sprint 97 Feature 97.5: SKILL.md Visual Editor (4 SP)
 *
 * Features:
 * - Frontmatter form editor (name, version, description, etc.)
 * - Markdown editor with preview toggle
 * - Save changes to SKILL.md
 *
 * Route: /admin/skills/:skillName/skill-md
 */

import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Save, Eye, EyeOff, Plus, X } from 'lucide-react';
import { getSkillMd, updateSkillMd } from '../../api/skills';
import type { SkillMdDocument } from '../../types/skills';
import { AdminNavigationBar } from '../../components/admin/AdminNavigationBar';

export function SkillMdEditor() {
  const { skillName } = useParams<{ skillName: string }>();

  // Editor state
  const [document, setDocument] = useState<SkillMdDocument | null>(null);
  const [originalDocument, setOriginalDocument] = useState<SkillMdDocument | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  // Preview state
  const [showPreview, setShowPreview] = useState(false);

  // Loading and error state
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load SKILL.md
  const loadDocument = useCallback(async () => {
    if (!skillName) return;

    setLoading(true);
    setError(null);

    try {
      const doc = await getSkillMd(skillName);
      setDocument(doc);
      setOriginalDocument(doc);
      setIsDirty(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load SKILL.md');
    } finally {
      setLoading(false);
    }
  }, [skillName]);

  // Initial load
  useEffect(() => {
    void loadDocument();
  }, [loadDocument]);

  // Track changes
  useEffect(() => {
    if (!document || !originalDocument) return;

    const isChanged =
      JSON.stringify(document.frontmatter) !== JSON.stringify(originalDocument.frontmatter) ||
      document.instructions !== originalDocument.instructions;

    setIsDirty(isChanged);
  }, [document, originalDocument]);

  // Save document
  const handleSave = async () => {
    if (!skillName || !document) return;

    setSaving(true);
    setError(null);

    try {
      const updated = await updateSkillMd(skillName, document);
      setDocument(updated);
      setOriginalDocument(updated);
      setIsDirty(false);
      alert('SKILL.md saved successfully!');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save SKILL.md');
    } finally {
      setSaving(false);
    }
  };

  // Update frontmatter field
  const updateFrontmatter = (field: keyof typeof document.frontmatter, value: string | string[]) => {
    if (!document) return;

    setDocument({
      ...document,
      frontmatter: {
        ...document.frontmatter,
        [field]: value,
      },
    });
  };

  // Update instructions
  const updateInstructions = (value: string) => {
    if (!document) return;

    setDocument({
      ...document,
      instructions: value,
    });
  };

  // Add/remove array items
  const addArrayItem = (field: 'triggers' | 'dependencies' | 'permissions' | 'tools', item: string) => {
    if (!document || !item.trim()) return;

    const currentArray = document.frontmatter[field] || [];
    updateFrontmatter(field, [...currentArray, item.trim()]);
  };

  const removeArrayItem = (field: 'triggers' | 'dependencies' | 'permissions' | 'tools', item: string) => {
    if (!document) return;

    const currentArray = document.frontmatter[field] || [];
    updateFrontmatter(field, currentArray.filter((i) => i !== item));
  };

  if (!skillName) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <p className="text-lg text-gray-600 dark:text-gray-400">Skill name is required</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mb-4">
        <AdminNavigationBar />
      </div>
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b-2 border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <Link
            to="/admin/skills/registry"
            className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Registry
          </Link>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                SKILL.md Editor: {skillName}
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Edit skill metadata and instructions
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="flex items-center gap-2 px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 rounded-lg transition-colors"
              >
                {showPreview ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                {showPreview ? 'Edit' : 'Preview'}
              </button>
              <button
                onClick={handleSave}
                disabled={!isDirty || saving}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Error Display */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
            <p className="text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-12 text-center">
            <p className="text-gray-600 dark:text-gray-400">Loading SKILL.md...</p>
          </div>
        )}

        {/* Editor */}
        {!loading && document && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column: Frontmatter Form */}
            <div className="space-y-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6">
                <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-4">
                  Metadata
                </h3>

                <div className="space-y-4">
                  {/* Name */}
                  <div>
                    <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                      Name
                    </label>
                    <input
                      type="text"
                      value={document.frontmatter.name}
                      onChange={(e) => updateFrontmatter('name', e.target.value)}
                      className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  {/* Version */}
                  <div>
                    <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                      Version
                    </label>
                    <input
                      type="text"
                      value={document.frontmatter.version}
                      onChange={(e) => updateFrontmatter('version', e.target.value)}
                      className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  {/* Description */}
                  <div>
                    <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                      Description
                    </label>
                    <textarea
                      value={document.frontmatter.description}
                      onChange={(e) => updateFrontmatter('description', e.target.value)}
                      rows={3}
                      className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  {/* Author */}
                  <div>
                    <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                      Author
                    </label>
                    <input
                      type="text"
                      value={document.frontmatter.author}
                      onChange={(e) => updateFrontmatter('author', e.target.value)}
                      className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  {/* Triggers */}
                  <ArrayField
                    label="Triggers"
                    items={document.frontmatter.triggers}
                    onAdd={(item) => addArrayItem('triggers', item)}
                    onRemove={(item) => removeArrayItem('triggers', item)}
                  />

                  {/* Dependencies */}
                  <ArrayField
                    label="Dependencies"
                    items={document.frontmatter.dependencies}
                    onAdd={(item) => addArrayItem('dependencies', item)}
                    onRemove={(item) => removeArrayItem('dependencies', item)}
                  />

                  {/* Permissions */}
                  <ArrayField
                    label="Permissions"
                    items={document.frontmatter.permissions}
                    onAdd={(item) => addArrayItem('permissions', item)}
                    onRemove={(item) => removeArrayItem('permissions', item)}
                  />
                </div>
              </div>
            </div>

            {/* Right Column: Instructions Editor */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-200 dark:border-gray-700 p-6">
              <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100 mb-4">
                Instructions
              </h3>

              {showPreview ? (
                <div className="prose dark:prose-invert max-w-none">
                  <div
                    className="text-sm text-gray-900 dark:text-gray-100"
                    dangerouslySetInnerHTML={{
                      __html: document.instructions
                        .split('\n')
                        .map((line) => `<p>${line}</p>`)
                        .join(''),
                    }}
                  />
                </div>
              ) : (
                <textarea
                  value={document.instructions}
                  onChange={(e) => updateInstructions(e.target.value)}
                  className="w-full h-[600px] font-mono text-sm bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-lg border border-gray-300 dark:border-gray-600 p-4 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter skill instructions in Markdown format..."
                  spellCheck={false}
                />
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ============================================================================
// ArrayField Component
// ============================================================================

interface ArrayFieldProps {
  label: string;
  items: string[];
  onAdd: (item: string) => void;
  onRemove: (item: string) => void;
}

function ArrayField({ label, items, onAdd, onRemove }: ArrayFieldProps) {
  const [newItem, setNewItem] = useState('');

  const handleAdd = () => {
    if (newItem.trim()) {
      onAdd(newItem);
      setNewItem('');
    }
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
        {label}
      </label>
      <div className="flex gap-2 mb-2">
        <input
          type="text"
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleAdd()}
          className="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder={`Add ${label.toLowerCase()}...`}
        />
        <button
          onClick={handleAdd}
          className="flex items-center gap-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <span
            key={item}
            className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 rounded-full text-sm"
          >
            {item}
            <button
              onClick={() => onRemove(item)}
              className="hover:text-gray-900 dark:hover:text-gray-100"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}

export default SkillMdEditor;
