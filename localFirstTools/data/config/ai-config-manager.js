/**
 * AI Configuration Manager for localFirstTools
 *
 * A standardized configuration system for AI-enabled applications.
 * Copy this entire script into your HTML file's <script> tag.
 *
 * Usage:
 *   const aiConfig = new AIConfigManager('my-app-name');
 *   const activeEndpoint = aiConfig.getActiveEndpoint();
 *   aiConfig.exportConfig();
 *   aiConfig.importConfig(jsonData);
 */

class AIConfigManager {
    constructor(appName = 'ai-app') {
        this.appName = appName;
        this.storageKey = `${appName}-ai-config`;
        this.config = this.loadConfig();
    }

    /**
     * Get default configuration template
     */
    getDefaultConfig() {
        return {
            _schema: "ai-config-v1",
            _description: "Standardized AI configuration for localFirstTools applications",
            endpoints: {
                default: {
                    id: "default",
                    name: "Local Default Bot",
                    url: "http://localhost:7071/api/businessinsightbot_function",
                    key: "",
                    guid: "",
                    active: false,
                    provider: "custom"
                }
            },
            speech: {
                azureTTSKey: "",
                azureTTSRegion: "eastus",
                ttsVoiceName: "en-US-JennyNeural",
                ttsProvider: "azure",
                speechRecognitionLang: "en-US",
                enableSpeech: true
            },
            llm: {
                provider: "custom",
                model: "gpt-4",
                temperature: 0.7,
                maxTokens: 2000,
                systemPrompt: ""
            },
            apiKeys: {
                openai: "",
                anthropic: "",
                azure: "",
                google: ""
            },
            preferences: {
                theme: "dark",
                autoSave: true,
                voiceEnabled: true,
                notifications: true
            },
            metadata: {
                exportDate: "",
                version: "1.0.0",
                appName: this.appName,
                lastModified: new Date().toISOString()
            }
        };
    }

    /**
     * Load configuration from localStorage
     */
    loadConfig() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (stored) {
                const config = JSON.parse(stored);
                // Validate schema version
                if (config._schema === "ai-config-v1") {
                    return config;
                }
            }
        } catch (error) {
            console.error('Error loading AI config:', error);
        }
        return this.getDefaultConfig();
    }

    /**
     * Save configuration to localStorage
     */
    saveConfig() {
        try {
            this.config.metadata.lastModified = new Date().toISOString();
            localStorage.setItem(this.storageKey, JSON.stringify(this.config));
            return true;
        } catch (error) {
            console.error('Error saving AI config:', error);
            return false;
        }
    }

    /**
     * Export configuration as JSON file
     */
    exportConfig() {
        try {
            const exportData = { ...this.config };
            exportData.metadata.exportDate = new Date().toISOString();

            const dataStr = JSON.stringify(exportData, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${this.appName}-ai-config-${new Date().toISOString().split('T')[0]}.json`;
            link.click();
            URL.revokeObjectURL(url);
            return true;
        } catch (error) {
            console.error('Error exporting AI config:', error);
            return false;
        }
    }

    /**
     * Import configuration from JSON data
     */
    importConfig(jsonData) {
        try {
            const imported = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;

            // Validate schema
            if (imported._schema !== "ai-config-v1") {
                throw new Error('Invalid configuration schema');
            }

            // Merge with defaults to ensure all fields exist
            this.config = this.mergeWithDefaults(imported);
            this.saveConfig();
            return true;
        } catch (error) {
            console.error('Error importing AI config:', error);
            return false;
        }
    }

    /**
     * Import configuration from file input event
     */
    importFromFile(event) {
        const file = event.target.files[0];
        if (!file) return Promise.reject('No file selected');

        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const success = this.importConfig(e.target.result);
                    if (success) {
                        resolve(this.config);
                    } else {
                        reject('Failed to import configuration');
                    }
                } catch (error) {
                    reject(error);
                }
            };
            reader.onerror = () => reject('Error reading file');
            reader.readAsText(file);
        });
    }

    /**
     * Merge imported config with defaults
     */
    mergeWithDefaults(imported) {
        const defaults = this.getDefaultConfig();
        return {
            ...defaults,
            ...imported,
            metadata: {
                ...defaults.metadata,
                ...imported.metadata,
                appName: this.appName
            }
        };
    }

    // ============ ENDPOINT MANAGEMENT ============

    /**
     * Add or update an endpoint
     */
    addEndpoint(endpoint) {
        if (!endpoint.id) {
            endpoint.id = this.generateId();
        }
        this.config.endpoints[endpoint.id] = {
            id: endpoint.id,
            name: endpoint.name || 'Unnamed Endpoint',
            url: endpoint.url || '',
            key: endpoint.key || '',
            guid: endpoint.guid || '',
            active: endpoint.active || false,
            provider: endpoint.provider || 'custom'
        };
        this.saveConfig();
        return endpoint.id;
    }

    /**
     * Remove an endpoint
     */
    removeEndpoint(endpointId) {
        if (this.config.endpoints[endpointId]) {
            delete this.config.endpoints[endpointId];
            this.saveConfig();
            return true;
        }
        return false;
    }

    /**
     * Set active endpoint (deactivates all others)
     */
    setActiveEndpoint(endpointId) {
        // Deactivate all
        Object.values(this.config.endpoints).forEach(ep => ep.active = false);

        // Activate selected
        if (this.config.endpoints[endpointId]) {
            this.config.endpoints[endpointId].active = true;
            this.saveConfig();
            return true;
        }
        return false;
    }

    /**
     * Get active endpoint
     */
    getActiveEndpoint() {
        return Object.values(this.config.endpoints).find(ep => ep.active) || null;
    }

    /**
     * Get all endpoints
     */
    getAllEndpoints() {
        return Object.values(this.config.endpoints);
    }

    // ============ SPEECH SETTINGS ============

    /**
     * Update speech settings
     */
    updateSpeechSettings(settings) {
        this.config.speech = { ...this.config.speech, ...settings };
        this.saveConfig();
    }

    /**
     * Get speech settings
     */
    getSpeechSettings() {
        return this.config.speech;
    }

    // ============ LLM SETTINGS ============

    /**
     * Update LLM settings
     */
    updateLLMSettings(settings) {
        this.config.llm = { ...this.config.llm, ...settings };
        this.saveConfig();
    }

    /**
     * Get LLM settings
     */
    getLLMSettings() {
        return this.config.llm;
    }

    // ============ API KEYS ============

    /**
     * Set API key for a provider
     */
    setAPIKey(provider, key) {
        this.config.apiKeys[provider] = key;
        this.saveConfig();
    }

    /**
     * Get API key for a provider
     */
    getAPIKey(provider) {
        return this.config.apiKeys[provider] || '';
    }

    // ============ PREFERENCES ============

    /**
     * Update preferences
     */
    updatePreferences(prefs) {
        this.config.preferences = { ...this.config.preferences, ...prefs };
        this.saveConfig();
    }

    /**
     * Get preferences
     */
    getPreferences() {
        return this.config.preferences;
    }

    // ============ UTILITIES ============

    /**
     * Generate unique ID
     */
    generateId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * Reset to defaults
     */
    resetToDefaults() {
        this.config = this.getDefaultConfig();
        this.saveConfig();
    }

    /**
     * Get full configuration
     */
    getConfig() {
        return { ...this.config };
    }
}

// ============ UI HELPER FUNCTIONS ============

/**
 * Create import/export UI buttons
 * Call this function to add standardized import/export buttons to your app
 */
function createAIConfigUI(aiConfig, containerId = 'ai-config-controls') {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container #${containerId} not found`);
        return;
    }

    container.innerHTML = `
        <div style="display: flex; gap: 10px; align-items: center;">
            <button onclick="window.aiConfigManager.exportConfig()"
                    style="padding: 8px 16px; cursor: pointer; border-radius: 4px; border: 1px solid #ccc; background: #f5f5f5;">
                📤 Export AI Config
            </button>
            <button onclick="document.getElementById('ai-config-import').click()"
                    style="padding: 8px 16px; cursor: pointer; border-radius: 4px; border: 1px solid #ccc; background: #f5f5f5;">
                📥 Import AI Config
            </button>
            <input type="file"
                   id="ai-config-import"
                   accept=".json"
                   style="display: none;"
                   onchange="handleAIConfigImport(event)">
        </div>
    `;
}

/**
 * Handle config import from file input
 */
function handleAIConfigImport(event) {
    if (!window.aiConfigManager) {
        console.error('AIConfigManager not initialized');
        return;
    }

    window.aiConfigManager.importFromFile(event)
        .then(() => {
            alert('AI configuration imported successfully! Reloading...');
            location.reload();
        })
        .catch(error => {
            alert(`Failed to import configuration: ${error}`);
        });
}

// Example usage (copy this into your app):
/*
// Initialize the config manager
const aiConfig = new AIConfigManager('my-app-name');
window.aiConfigManager = aiConfig; // Make globally available

// Get active endpoint
const activeEndpoint = aiConfig.getActiveEndpoint();
if (activeEndpoint) {
    console.log('Using endpoint:', activeEndpoint.url);
}

// Add a new endpoint
aiConfig.addEndpoint({
    name: 'Production Bot',
    url: 'https://api.example.com/bot',
    key: 'your-api-key',
    active: true
});

// Get speech settings
const speechSettings = aiConfig.getSpeechSettings();
console.log('TTS Voice:', speechSettings.ttsVoiceName);
*/
