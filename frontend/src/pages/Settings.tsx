/**
 * Settings Page
 * Sprint 28 Feature 28.3: User settings and preferences
 *
 * Features:
 * - Tabbed interface (General, Models, Advanced)
 * - Form validation
 * - localStorage persistence via SettingsContext
 * - Toast notifications for save/reset actions
 * - Danger zone for destructive actions
 */

import { useState, useEffect } from 'react';
import { useSettings } from '../contexts/SettingsContext';
import { AVAILABLE_MODELS, CLOUD_PROVIDERS, RETRIEVAL_METHODS } from '../types/settings';

type TabType = 'general' | 'models' | 'advanced';

export function Settings() {
  const { settings, updateSettings, resetSettings } = useSettings();
  const [activeTab, setActiveTab] = useState<TabType>('general');
  const [hasChanges, setHasChanges] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [showClearConversationsConfirm, setShowClearConversationsConfirm] = useState(false);

  // Local form state
  const [formData, setFormData] = useState(settings);

  // Check if form has changes
  useEffect(() => {
    const changed = JSON.stringify(formData) !== JSON.stringify(settings);
    setHasChanges(changed);
  }, [formData, settings]);

  const handleSave = () => {
    // Validate ollamaBaseUrl
    if (formData.ollamaBaseUrl && !isValidUrl(formData.ollamaBaseUrl)) {
      showNotification('Ungueltige Ollama Base URL');
      return;
    }

    updateSettings(formData);
    setHasChanges(false);
    showNotification('Einstellungen gespeichert');
  };

  const handleReset = () => {
    resetSettings();
    setFormData(settings);
    setShowResetConfirm(false);
    setHasChanges(false);
    showNotification('Einstellungen zurueckgesetzt');
  };

  const handleClearConversations = () => {
    localStorage.removeItem('aegis-chat-history');
    setShowClearConversationsConfirm(false);
    showNotification('Konversationen geloescht');
  };

  const handleExportConversations = () => {
    const history = localStorage.getItem('aegis-chat-history');
    if (!history) {
      showNotification('Keine Konversationen zum Exportieren');
      return;
    }

    const blob = new Blob([history], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aegis-conversations-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showNotification('Konversationen exportiert');
  };

  const handleImportConversations = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        JSON.parse(content); // Validate JSON
        localStorage.setItem('aegis-chat-history', content);
        showNotification('Konversationen importiert');
      } catch {
        showNotification('Fehler beim Importieren');
      }
    };
    reader.readAsText(file);
  };

  const showNotification = (message: string) => {
    setToastMessage(message);
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  };

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Einstellungen</h1>
        <p className="text-gray-600">Passen Sie AegisRAG an Ihre Beduerfnisse an</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('general')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'general'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Allgemein
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'models'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Modelle
          </button>
          <button
            onClick={() => setActiveTab('advanced')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'advanced'
                ? 'border-primary text-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Erweitert
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        {/* General Tab */}
        {activeTab === 'general' && (
          <div className="space-y-6">
            {/* Theme */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Theme
              </label>
              <div className="flex space-x-4">
                {(['light', 'dark', 'auto'] as const).map((theme) => (
                  <button
                    key={theme}
                    onClick={() => setFormData({ ...formData, theme })}
                    className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                      formData.theme === theme
                        ? 'border-primary bg-primary bg-opacity-10 text-primary'
                        : 'border-gray-300 text-gray-700 hover:border-gray-400'
                    }`}
                  >
                    {theme === 'light' && 'Hell'}
                    {theme === 'dark' && 'Dunkel'}
                    {theme === 'auto' && 'Auto (System)'}
                  </button>
                ))}
              </div>
            </div>

            {/* Language */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sprache
              </label>
              <div className="flex space-x-4">
                <button
                  onClick={() => setFormData({ ...formData, language: 'de' })}
                  className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                    formData.language === 'de'
                      ? 'border-primary bg-primary bg-opacity-10 text-primary'
                      : 'border-gray-300 text-gray-700 hover:border-gray-400'
                  }`}
                >
                  Deutsch
                </button>
                <button
                  onClick={() => setFormData({ ...formData, language: 'en' })}
                  className={`flex-1 py-2 px-4 rounded-lg border-2 transition-colors ${
                    formData.language === 'en'
                      ? 'border-primary bg-primary bg-opacity-10 text-primary'
                      : 'border-gray-300 text-gray-700 hover:border-gray-400'
                  }`}
                >
                  English
                </button>
              </div>
            </div>

            {/* Auto-save Conversations */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Konversationen automatisch speichern
                </label>
                <p className="text-sm text-gray-500 mt-1">
                  Speichert Ihre Unterhaltungen lokal im Browser
                </p>
              </div>
              <button
                onClick={() =>
                  setFormData({ ...formData, autoSaveConversations: !formData.autoSaveConversations })
                }
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  formData.autoSaveConversations ? 'bg-primary' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    formData.autoSaveConversations ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        )}

        {/* Models Tab */}
        {activeTab === 'models' && (
          <div className="space-y-6">
            {/* Ollama Base URL */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Ollama Base URL
              </label>
              <input
                type="text"
                value={formData.ollamaBaseUrl}
                onChange={(e) => setFormData({ ...formData, ollamaBaseUrl: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="http://localhost:11434"
              />
              <p className="text-sm text-gray-500 mt-1">
                URL Ihres Ollama-Servers fuer lokale Modelle
              </p>
            </div>

            {/* Default Model */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Standard-Modell
              </label>
              <select
                value={formData.defaultModel}
                onChange={(e) => setFormData({ ...formData, defaultModel: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {AVAILABLE_MODELS.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </div>

            {/* Cloud Provider */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Cloud-Anbieter
              </label>
              <select
                value={formData.cloudProvider}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    cloudProvider: e.target.value as 'local' | 'alibaba' | 'openai',
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {CLOUD_PROVIDERS.map((provider) => (
                  <option key={provider.value} value={provider.value}>
                    {provider.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Cloud API Key */}
            {formData.cloudProvider !== 'local' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Cloud API Key
                </label>
                <input
                  type="password"
                  value={formData.cloudApiKey || ''}
                  onChange={(e) => setFormData({ ...formData, cloudApiKey: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="sk-..."
                />
                <p className="text-sm text-gray-500 mt-1">
                  API-Schluessel fuer {CLOUD_PROVIDERS.find((p) => p.value === formData.cloudProvider)?.label}
                </p>
              </div>
            )}

            {/* Retrieval Method (Sprint 74 Feature 74.3) */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Retrieval-Methode
              </label>
              <div className="space-y-3">
                {RETRIEVAL_METHODS.map((method) => (
                  <button
                    key={method.value}
                    onClick={() =>
                      setFormData({
                        ...formData,
                        retrievalMethod: method.value as 'hybrid' | 'vector' | 'bm25',
                      })
                    }
                    className={`w-full text-left p-4 rounded-lg border-2 transition-colors ${
                      formData.retrievalMethod === method.value
                        ? 'border-primary bg-primary bg-opacity-10'
                        : 'border-gray-300 hover:border-gray-400'
                    }`}
                  >
                    <div className="flex items-start">
                      {/* Radio indicator */}
                      <div className="flex-shrink-0 mt-0.5 mr-3">
                        <div
                          className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                            formData.retrievalMethod === method.value
                              ? 'border-primary'
                              : 'border-gray-300'
                          }`}
                        >
                          {formData.retrievalMethod === method.value && (
                            <div className="w-2.5 h-2.5 rounded-full bg-primary" />
                          )}
                        </div>
                      </div>
                      {/* Method info */}
                      <div>
                        <div className="font-medium text-gray-900">{method.label}</div>
                        <div className="text-sm text-gray-600 mt-1">{method.description}</div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
              <p className="text-sm text-gray-500 mt-2">
                Wählen Sie die Retrieval-Methode für Ihre Suchanfragen. Hybrid (empfohlen) kombiniert semantische und Keyword-Suche für beste Ergebnisse.
              </p>
            </div>
          </div>
        )}

        {/* Advanced Tab */}
        {activeTab === 'advanced' && (
          <div className="space-y-6">
            {/* Export Conversations */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Daten exportieren</h3>
              <button
                onClick={handleExportConversations}
                className="w-full py-2 px-4 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Konversationen als JSON exportieren
              </button>
            </div>

            {/* Import Conversations */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">Daten importieren</h3>
              <label className="w-full py-2 px-4 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors cursor-pointer block text-center">
                Konversationen importieren
                <input
                  type="file"
                  accept=".json"
                  onChange={handleImportConversations}
                  className="hidden"
                />
              </label>
            </div>

            {/* Danger Zone */}
            <div className="border-2 border-red-200 rounded-lg p-4 bg-red-50">
              <h3 className="text-sm font-medium text-red-900 mb-3">Danger Zone</h3>

              {/* Clear Conversations */}
              <div className="mb-3">
                {!showClearConversationsConfirm ? (
                  <button
                    onClick={() => setShowClearConversationsConfirm(true)}
                    className="w-full py-2 px-4 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
                  >
                    Alle Konversationen loeschen
                  </button>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-red-800">
                      Sind Sie sicher? Diese Aktion kann nicht rueckgaengig gemacht werden.
                    </p>
                    <div className="flex space-x-2">
                      <button
                        onClick={handleClearConversations}
                        className="flex-1 py-2 px-4 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                      >
                        Ja, loeschen
                      </button>
                      <button
                        onClick={() => setShowClearConversationsConfirm(false)}
                        className="flex-1 py-2 px-4 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
                      >
                        Abbrechen
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Reset Settings */}
              <div>
                {!showResetConfirm ? (
                  <button
                    onClick={() => setShowResetConfirm(true)}
                    className="w-full py-2 px-4 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
                  >
                    Einstellungen zuruecksetzen
                  </button>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-red-800">
                      Alle Einstellungen auf Standardwerte zuruecksetzen?
                    </p>
                    <div className="flex space-x-2">
                      <button
                        onClick={handleReset}
                        className="flex-1 py-2 px-4 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                      >
                        Zuruecksetzen
                      </button>
                      <button
                        onClick={() => setShowResetConfirm(false)}
                        className="flex-1 py-2 px-4 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
                      >
                        Abbrechen
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Save Button */}
      <div className="mt-6 flex justify-end">
        <button
          onClick={handleSave}
          disabled={!hasChanges}
          className={`py-2 px-6 rounded-lg font-medium transition-colors ${
            hasChanges
              ? 'bg-primary text-white hover:bg-primary-hover'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          Speichern
        </button>
      </div>

      {/* Toast Notification */}
      {showToast && (
        <div className="fixed bottom-4 right-4 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg animate-fade-in">
          {toastMessage}
        </div>
      )}
    </div>
  );
}
