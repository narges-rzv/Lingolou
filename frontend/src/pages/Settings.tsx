import { useState, useEffect } from 'react';
import { apiFetch } from '../api';
import type { ApiKeysStatus, ApiKeysUpdate } from '../types';

export default function Settings() {
  const [openaiKey, setOpenaiKey] = useState('');
  const [elevenlabsKey, setElevenlabsKey] = useState('');
  const [status, setStatus] = useState<ApiKeysStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    apiFetch('/auth/api-keys')
      .then(setStatus)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const body: ApiKeysUpdate = {};
      if (openaiKey) body.openai_api_key = openaiKey;
      if (elevenlabsKey) body.elevenlabs_api_key = elevenlabsKey;
      const updated = await apiFetch('/auth/api-keys', {
        method: 'PUT',
        json: body,
      });
      setStatus(updated);
      setOpenaiKey('');
      setElevenlabsKey('');
      setMessage('Keys saved successfully.');
    } catch (err) {
      setMessage(`Error: ${(err as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async (keyType: 'openai' | 'elevenlabs') => {
    setSaving(true);
    setMessage(null);
    try {
      const body: ApiKeysUpdate = {};
      if (keyType === 'openai') body.openai_api_key = '';
      if (keyType === 'elevenlabs') body.elevenlabs_api_key = '';
      const updated = await apiFetch('/auth/api-keys', {
        method: 'PUT',
        json: body,
      });
      setStatus(updated);
      setMessage('Key removed.');
    } catch (err) {
      setMessage(`Error: ${(err as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="page-card settings-page">
      <h1>Settings</h1>

      <section className="settings-section">
        <h2>API Keys</h2>
        <p className="settings-description">
          Provide your own API keys to generate stories and audio without limits.
          Keys are encrypted and stored securely.
        </p>

        {message && (
          <div className={message.startsWith('Error') ? 'error-message' : 'success-message'}>
            {message}
          </div>
        )}

        <form onSubmit={handleSave}>
          <div className="api-key-field">
            <label>
              OpenAI API Key
              {status?.has_openai_key
                ? <span className="key-status key-status-set">Configured</span>
                : <span className="key-status key-status-missing">Not set</span>
              }
            </label>
            <div className="api-key-input-row">
              <input
                type="password"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder={status?.has_openai_key ? '••••••••••••••••' : 'sk-...'}
              />
              {status?.has_openai_key && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => handleRemove('openai')} disabled={saving}>
                  Remove
                </button>
              )}
            </div>
            <span className="field-hint">
              Get your key at <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer">platform.openai.com/api-keys</a>
            </span>
          </div>

          <div className="api-key-field">
            <label>
              ElevenLabs API Key
              {status?.has_elevenlabs_key
                ? <span className="key-status key-status-set">Configured</span>
                : <span className="key-status key-status-missing">Not set</span>
              }
            </label>
            <div className="api-key-input-row">
              <input
                type="password"
                value={elevenlabsKey}
                onChange={(e) => setElevenlabsKey(e.target.value)}
                placeholder={status?.has_elevenlabs_key ? '••••••••••••••••' : 'Your ElevenLabs API key'}
              />
              {status?.has_elevenlabs_key && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => handleRemove('elevenlabs')} disabled={saving}>
                  Remove
                </button>
              )}
            </div>
            <span className="field-hint">
              Get your key at <a href="https://elevenlabs.io/app/settings/api-keys" target="_blank" rel="noopener noreferrer">elevenlabs.io settings</a>
            </span>
          </div>

          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={saving || (!openaiKey && !elevenlabsKey)}>
              {saving ? 'Saving...' : 'Save Keys'}
            </button>
          </div>
        </form>
      </section>

      <section className="settings-section">
        <h2>Free Tier Usage</h2>
        {status && (
          <div className="free-tier-info">
            <p>
              Free story generations used: <strong>{status.free_stories_used} / {status.free_stories_limit}</strong>
            </p>
            {status.free_stories_used >= status.free_stories_limit && !status.has_openai_key && (
              <p className="field-hint">
                You've used all free story generations. Add your own OpenAI API key above to continue creating stories.
              </p>
            )}
            {status.free_stories_used < status.free_stories_limit && !status.has_openai_key && (
              <p className="field-hint">
                You have {status.free_stories_limit - status.free_stories_used} free story generation{status.free_stories_limit - status.free_stories_used !== 1 ? 's' : ''} remaining.
              </p>
            )}
            {status.has_openai_key && (
              <p className="field-hint">
                You're using your own OpenAI key — no limits on story generation.
              </p>
            )}
            <p>
              Free audio generations used: <strong>{status.free_audio_used} / {status.free_audio_limit}</strong>
            </p>
            {status.free_audio_used >= status.free_audio_limit && !status.has_elevenlabs_key && (
              <p className="field-hint">
                You've used all free audio generations. Add your own ElevenLabs API key above to continue generating audio.
              </p>
            )}
            {status.free_audio_used < status.free_audio_limit && !status.has_elevenlabs_key && (
              <p className="field-hint">
                You have {status.free_audio_limit - status.free_audio_used} free audio generation{status.free_audio_limit - status.free_audio_used !== 1 ? 's' : ''} remaining.
              </p>
            )}
            {status.has_elevenlabs_key && (
              <p className="field-hint">
                You're using your own ElevenLabs key — no limits on audio generation.
              </p>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
