import { useState, useEffect } from 'react';
import { apiFetch } from '../api';
import { VoiceSettings, VoiceListItem, VoiceConfigResponse } from '../types';

interface VoiceAssignmentModalProps {
  storyId: string;
  onConfirm: (override: Record<string, Record<string, unknown>>) => void;
  onCancel: () => void;
}

export default function VoiceAssignmentModal({ storyId, onConfirm, onCancel }: VoiceAssignmentModalProps) {
  const [speakers, setSpeakers] = useState<string[]>([]);
  const [voiceConfig, setVoiceConfig] = useState<Record<string, VoiceSettings>>({});
  const [availableVoices, setAvailableVoices] = useState<VoiceListItem[]>([]);
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewSpeaker, setPreviewSpeaker] = useState<string | null>(null);
  const [previewAudio, setPreviewAudio] = useState<HTMLAudioElement | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [configData, voices] = await Promise.all([
          apiFetch(`/stories/${storyId}/voice-config`) as Promise<VoiceConfigResponse>,
          (apiFetch('/stories/voices') as Promise<VoiceListItem[]>).catch(() => [] as VoiceListItem[]),
        ]);

        if (cancelled) return;

        setSpeakers(configData.speakers);
        setVoiceConfig(configData.voice_config);
        setAvailableVoices(voices);

        // Initialize assignments from defaults
        const initial: Record<string, string> = {};
        for (const speaker of configData.speakers) {
          const cfg = configData.voice_config[speaker];
          initial[speaker] = cfg?.voice_id || '';
        }
        setAssignments(initial);
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [storyId]);

  const handleVoiceChange = (speaker: string, voiceId: string) => {
    setAssignments((prev) => ({ ...prev, [speaker]: voiceId }));
  };

  const handlePreview = (speaker: string) => {
    // Stop current preview
    if (previewAudio) {
      previewAudio.pause();
      previewAudio.currentTime = 0;
    }
    // Toggle off if same speaker
    if (previewSpeaker === speaker) {
      setPreviewSpeaker(null);
      setPreviewAudio(null);
      return;
    }
    const voiceId = assignments[speaker];
    const voice = availableVoices.find((v) => v.voice_id === voiceId);
    if (!voice?.preview_url) return;

    const audio = new Audio(voice.preview_url);
    audio.onended = () => {
      setPreviewSpeaker(null);
      setPreviewAudio(null);
    };
    audio.onerror = () => {
      setPreviewSpeaker(null);
      setPreviewAudio(null);
    };
    setPreviewSpeaker(speaker);
    setPreviewAudio(audio);
    audio.play().catch(() => {
      setPreviewSpeaker(null);
      setPreviewAudio(null);
    });
  };

  const handleConfirm = () => {
    // Build voice override map: only include speakers with a selected voice
    const override: Record<string, Record<string, unknown>> = {};
    for (const speaker of speakers) {
      const voiceId = assignments[speaker];
      if (!voiceId) continue;

      // Start from existing config for this speaker, or empty
      const base = voiceConfig[speaker] || {};
      override[speaker] = { ...base, voice_id: voiceId };
    }
    onConfirm(override);
  };

  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div
        className="confirm-dialog"
        style={{ maxWidth: '560px' }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginTop: 0, marginBottom: '1rem' }}>Voice Assignments</h3>

        {loading && <p>Loading voice config...</p>}
        {error && <div className="error-message">{error}</div>}

        {!loading && !error && speakers.length === 0 && (
          <p style={{ color: 'var(--color-text-secondary)' }}>
            No speakers found in story scripts. Generate the story first.
          </p>
        )}

        {!loading && !error && speakers.length > 0 && (
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid var(--glass-border)' }}>
                    Speaker
                  </th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', borderBottom: '1px solid var(--glass-border)' }}>
                    Voice
                  </th>
                  <th style={{ width: '40px', padding: '0.5rem', borderBottom: '1px solid var(--glass-border)' }} />
                </tr>
              </thead>
              <tbody>
                {speakers.map((speaker) => (
                  <tr key={speaker}>
                    <td style={{ padding: '0.5rem', fontWeight: 500 }}>{speaker}</td>
                    <td style={{ padding: '0.5rem' }}>
                      {availableVoices.length > 0 ? (
                        <select
                          value={assignments[speaker] || ''}
                          onChange={(e) => handleVoiceChange(speaker, e.target.value)}
                          style={{ width: '100%' }}
                        >
                          <option value="">-- Select Voice --</option>
                          {availableVoices.map((v) => (
                            <option key={v.voice_id} value={v.voice_id}>
                              {v.name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="text"
                          placeholder="Voice ID"
                          value={assignments[speaker] || ''}
                          onChange={(e) => handleVoiceChange(speaker, e.target.value)}
                          style={{ width: '100%' }}
                        />
                      )}
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                      {assignments[speaker] && availableVoices.find((v) => v.voice_id === assignments[speaker])?.preview_url && (
                        <button
                          className={`btn-line-audio ${previewSpeaker === speaker ? 'playing' : ''}`}
                          onClick={() => handlePreview(speaker)}
                          title={previewSpeaker === speaker ? 'Stop preview' : 'Preview voice'}
                        >
                          {previewSpeaker === speaker ? '\u25A0' : '\u25B6'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="confirm-actions" style={{ marginTop: '1.25rem' }}>
          <button className="btn btn-ghost" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleConfirm}
            disabled={loading || speakers.length === 0}
          >
            Confirm & Generate
          </button>
        </div>
      </div>
    </div>
  );
}
