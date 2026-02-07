import { useState, useEffect } from 'react';
import { apiFetch } from '../api';

const SPEAKER_COLORS = {};
let colorIndex = 0;

function getSpeakerClass(speaker) {
  if (!speaker) return '';
  if (!(speaker in SPEAKER_COLORS)) {
    SPEAKER_COLORS[speaker] = `speaker-${colorIndex % 6}`;
    colorIndex++;
  }
  return SPEAKER_COLORS[speaker];
}

function EditableField({ value, onChange, className, multiline, dir }) {
  if (multiline) {
    return (
      <textarea
        className={`edit-field ${className || ''}`}
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        rows={2}
        dir={dir}
      />
    );
  }
  return (
    <input
      className={`edit-field ${className || ''}`}
      type="text"
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      dir={dir}
    />
  );
}

const ENTRY_TYPES = [
  { value: 'line', label: 'Dialogue' },
  { value: 'scene', label: 'Scene' },
  { value: 'pause', label: 'Pause' },
  { value: 'sfx', label: 'Sound Effect' },
  { value: 'bg', label: 'Background' },
  { value: 'music', label: 'Music' },
];

function newEntry(type) {
  switch (type) {
    case 'line': return { type: 'line', speaker: '', lang: 'en', text: '', emotion: '' };
    case 'scene': return { type: 'scene', text: '' };
    case 'pause': return { type: 'pause', seconds: 1 };
    case 'sfx': return { type: 'sfx', text: '' };
    case 'bg': return { type: 'bg', value: '' };
    case 'music': return { type: 'music', value: '' };
    default: return { type: 'line', speaker: '', lang: 'en', text: '' };
  }
}

function InsertBar({ onInsert }) {
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <div className="insert-bar">
        <button className="insert-btn" onClick={() => setOpen(true)} title="Insert entry here">+</button>
      </div>
    );
  }
  return (
    <div className="insert-bar insert-bar-open">
      {ENTRY_TYPES.map((t) => (
        <button
          key={t.value}
          className="btn btn-ghost btn-sm"
          onClick={() => { onInsert(t.value); setOpen(false); }}
        >
          + {t.label}
        </button>
      ))}
      <button className="btn btn-ghost btn-sm" onClick={() => setOpen(false)}>Cancel</button>
    </div>
  );
}

function ScriptEntry({ entry, index, editing, onUpdate, onDelete }) {
  const type = entry.type || '';

  const update = (field, value) => {
    onUpdate(index, { ...entry, [field]: value });
  };

  // Dialogue / line
  if (type === 'line' || type === 'dialogue' || entry.speaker) {
    if (editing) {
      return (
        <div className="script-entry script-dialogue edit-entry">
          <div className="edit-row">
            <label className="edit-label">Speaker</label>
            <EditableField value={entry.speaker} onChange={(v) => update('speaker', v)} />
            <label className="edit-label">Lang</label>
            <EditableField value={entry.lang || entry.language} onChange={(v) => update('lang', v)} />
            {entry.emotion !== undefined && (
              <>
                <label className="edit-label">Emotion</label>
                <EditableField value={entry.emotion} onChange={(v) => update('emotion', v)} />
              </>
            )}
            <button className="btn-delete-entry" onClick={() => onDelete(index)} title="Remove entry">&times;</button>
          </div>
          <div className="edit-row">
            <label className="edit-label">Text</label>
            <EditableField value={entry.text} onChange={(v) => update('text', v)} className="edit-field-wide" dir={entry.lang === 'fa' ? 'rtl' : undefined} />
          </div>
          {(entry.transliteration !== undefined || entry.lang === 'fa') && (
            <div className="edit-row">
              <label className="edit-label">Translit.</label>
              <EditableField value={entry.transliteration} onChange={(v) => update('transliteration', v)} className="edit-field-wide" />
            </div>
          )}
          {(entry.gloss_en !== undefined || entry.translation !== undefined || entry.english !== undefined) && (
            <div className="edit-row">
              <label className="edit-label">English</label>
              <EditableField
                value={entry.gloss_en || entry.translation || entry.english}
                onChange={(v) => update(entry.gloss_en !== undefined ? 'gloss_en' : entry.translation !== undefined ? 'translation' : 'english', v)}
                className="edit-field-wide"
              />
            </div>
          )}
        </div>
      );
    }

    return (
      <div className="script-entry script-dialogue">
        <span className={`speaker ${getSpeakerClass(entry.speaker)}`}>
          {entry.speaker}
        </span>
        {(entry.lang || entry.language) && <span className="lang-tag">{entry.lang || entry.language}</span>}
        {entry.emotion && <span className="script-emotion">[{entry.emotion}]</span>}
        {entry.text && <span className="farsi-text">{entry.text}</span>}
        {entry.transliteration && (
          <span className="transliteration">{entry.transliteration}</span>
        )}
        {(entry.gloss_en || entry.translation || entry.english) && (
          <>
            {' '}
            <span className="gloss">({entry.gloss_en || entry.translation || entry.english})</span>
          </>
        )}
      </div>
    );
  }

  // Scene
  if (type === 'scene' || type === 'scene_heading') {
    const text = entry.text || entry.description || entry.heading || entry.title || '';
    if (editing) {
      return (
        <div className="script-entry script-scene edit-entry">
          <div className="edit-row">
            <label className="edit-label">Scene</label>
            <EditableField value={text} onChange={(v) => update(entry.title !== undefined ? 'title' : 'text', v)} className="edit-field-wide" />
            <button className="btn-delete-entry" onClick={() => onDelete(index)} title="Remove entry">&times;</button>
          </div>
        </div>
      );
    }
    return <div className="script-entry script-scene">{text}</div>;
  }

  // Pause
  if (type === 'pause') {
    if (editing) {
      return (
        <div className="script-entry script-pause edit-entry">
          <div className="edit-row">
            <label className="edit-label">Pause (sec)</label>
            <EditableField value={entry.seconds || entry.duration || ''} onChange={(v) => update('seconds', Number(v) || v)} />
            <button className="btn-delete-entry" onClick={() => onDelete(index)} title="Remove entry">&times;</button>
          </div>
        </div>
      );
    }
    return (
      <div className="script-entry script-pause">
        [pause{entry.seconds ? ` ${entry.seconds}s` : entry.duration ? ` ${entry.duration}s` : ''}]
      </div>
    );
  }

  // SFX
  if (type === 'sfx' || type === 'sound_effect') {
    const text = entry.value || entry.text || entry.description || '';
    if (editing) {
      return (
        <div className="script-entry script-sfx edit-entry">
          <div className="edit-row">
            <label className="edit-label">SFX</label>
            <EditableField value={text} onChange={(v) => update(entry.value !== undefined ? 'value' : 'text', v)} className="edit-field-wide" />
            <button className="btn-delete-entry" onClick={() => onDelete(index)} title="Remove entry">&times;</button>
          </div>
        </div>
      );
    }
    return <div className="script-entry script-sfx">SFX: {text}</div>;
  }

  // BG / Music / Performance / End / other
  if (type === 'bg' || type === 'music' || type === 'performance' || type === 'end') {
    const text = entry.value || entry.text || '';
    if (editing) {
      return (
        <div className="script-entry edit-entry">
          <div className="edit-row">
            <label className="edit-label">{type}</label>
            <EditableField value={text} onChange={(v) => update('value', v)} className="edit-field-wide" />
            <button className="btn-delete-entry" onClick={() => onDelete(index)} title="Remove entry">&times;</button>
          </div>
        </div>
      );
    }
    return <div className="script-entry" style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>[{type}: {text}]</div>;
  }

  // Fallback
  if (entry.text) {
    if (editing) {
      return (
        <div className="script-entry edit-entry">
          <div className="edit-row">
            <label className="edit-label">Text</label>
            <EditableField value={entry.text} onChange={(v) => update('text', v)} className="edit-field-wide" />
            <button className="btn-delete-entry" onClick={() => onDelete(index)} title="Remove entry">&times;</button>
          </div>
        </div>
      );
    }
    return <div className="script-entry">{entry.text}</div>;
  }

  return null;
}

export default function ScriptViewer({ storyId, chapterNumber }) {
  const [script, setScript] = useState(null);
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setEditing(false);
    setDirty(false);
    apiFetch(`/stories/${storyId}/chapters/${chapterNumber}/script?enhanced=true`)
      .then((data) => {
        setScript(data);
        const arr = Array.isArray(data)
          ? data
          : data.entries || data.script || data.lines || [];
        setEntries(Array.isArray(arr) ? arr : []);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [storyId, chapterNumber]);

  const [uploadError, setUploadError] = useState(null);

  const handleUpdate = (index, updatedEntry) => {
    setEntries((prev) => {
      const copy = [...prev];
      copy[index] = updatedEntry;
      return copy;
    });
    setDirty(true);
  };

  const handleDelete = (index) => {
    setEntries((prev) => prev.filter((_, i) => i !== index));
    setDirty(true);
  };

  const handleInsert = (afterIndex, type) => {
    setEntries((prev) => {
      const copy = [...prev];
      copy.splice(afterIndex + 1, 0, newEntry(type));
      return copy;
    });
    setDirty(true);
  };

  const handleAddAtEnd = (type) => {
    setEntries((prev) => [...prev, newEntry(type)]);
    setDirty(true);
  };

  const validateScriptJson = (data) => {
    // Accept an array of entries directly
    if (Array.isArray(data)) {
      if (data.length === 0) return 'JSON array is empty.';
      for (let i = 0; i < data.length; i++) {
        if (typeof data[i] !== 'object' || data[i] === null) {
          return `Entry ${i} is not an object.`;
        }
        // Each entry should have at least a type or speaker or text
        const e = data[i];
        if (!e.type && !e.speaker && !e.text) {
          return `Entry ${i} must have at least a "type", "speaker", or "text" field.`;
        }
      }
      return null;
    }
    // Accept an object with entries/script/lines array
    if (typeof data === 'object' && data !== null) {
      const arr = data.entries || data.script || data.lines;
      if (Array.isArray(arr)) {
        return validateScriptJson(arr);
      }
      return 'JSON object must contain an "entries", "script", or "lines" array.';
    }
    return 'JSON must be an array of entries or an object with an "entries" array.';
  };

  const handleUpload = (e) => {
    setUploadError(null);
    const file = e.target.files?.[0];
    if (!file) return;
    // Reset input so re-uploading same file works
    e.target.value = '';

    const reader = new FileReader();
    reader.onload = (evt) => {
      let data;
      try {
        data = JSON.parse(evt.target.result);
      } catch {
        setUploadError('Invalid JSON file.');
        return;
      }
      const err = validateScriptJson(data);
      if (err) {
        setUploadError(err);
        return;
      }
      // Extract entries
      const arr = Array.isArray(data)
        ? data
        : data.entries || data.script || data.lines || [];
      setEntries(arr);
      setScript(data);
      setDirty(true);
      setEditing(true);
    };
    reader.readAsText(file);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Rebuild the full script structure
      const toSave = Array.isArray(script)
        ? entries
        : { ...script, [script.entries ? 'entries' : script.script ? 'script' : script.lines ? 'lines' : 'entries']: entries };

      await apiFetch(`/stories/${storyId}/chapters/${chapterNumber}/script`, {
        method: 'PUT',
        json: Array.isArray(script) ? entries : toSave,
      });
      setDirty(false);
      setScript(Array.isArray(script) ? entries : toSave);
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDownload = () => {
    const data = Array.isArray(script) ? entries : script;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `story-${storyId}-chapter-${chapterNumber}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <div className="script-loading">Loading script...</div>;
  if (error) return <div className="script-loading">{error}</div>;
  if (!script) return <div className="script-loading">No script available</div>;

  if (entries.length === 0) {
    return (
      <div className="script-viewer">
        <div className="script-toolbar">
          <button className="btn btn-ghost btn-sm" onClick={handleDownload}>Download JSON</button>
          <label className="btn btn-ghost btn-sm upload-label">
            Upload JSON
            <input type="file" accept=".json,application/json" onChange={handleUpload} hidden />
          </label>
        </div>
        {uploadError && <div className="upload-error">{uploadError}</div>}
        <pre style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
          {JSON.stringify(script, null, 2)}
        </pre>
      </div>
    );
  }

  return (
    <div className="script-viewer">
      <div className="script-toolbar">
        <button
          className={`btn btn-sm ${editing ? 'btn-primary' : 'btn-ghost'}`}
          onClick={() => setEditing(!editing)}
        >
          {editing ? 'Done Editing' : 'Edit Script'}
        </button>
        {dirty && (
          <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        )}
        <button className="btn btn-ghost btn-sm" onClick={handleDownload}>Download JSON</button>
        <label className="btn btn-ghost btn-sm upload-label">
          Upload JSON
          <input type="file" accept=".json,application/json" onChange={handleUpload} hidden />
        </label>
      </div>
      {uploadError && <div className="upload-error">{uploadError}</div>}
      {entries.map((entry, idx) => (
        <div key={idx}>
          <ScriptEntry
            entry={entry}
            index={idx}
            editing={editing}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
          />
          {editing && <InsertBar onInsert={(type) => handleInsert(idx, type)} />}
        </div>
      ))}
      {editing && (
        <div className="add-entry-section">
          <span className="add-entry-label">Add entry:</span>
          {ENTRY_TYPES.map((t) => (
            <button
              key={t.value}
              className="btn btn-ghost btn-sm"
              onClick={() => handleAddAtEnd(t.value)}
            >
              + {t.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
