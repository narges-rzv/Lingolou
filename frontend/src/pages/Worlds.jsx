import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api';

const PLACEHOLDER_TEMPLATE =
  'Write a story aimed for 4-8 year old kids about {theme}. ' +
  'The characters learn basic {language} words and phrases. ' +
  'The plot is: {plot}. Keep the story in {num_chapters} chapters.';

export default function Worlds() {
  const [worlds, setWorlds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreate, setShowCreate] = useState(false);

  // Create form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [promptTemplate, setPromptTemplate] = useState(PLACEHOLDER_TEMPLATE);
  const [characters, setCharacters] = useState([{ name: 'NARRATOR', description: 'Tells the story' }]);
  const [voiceConfig, setVoiceConfig] = useState({});
  const [visibility, setVisibility] = useState('private');
  const [creating, setCreating] = useState(false);

  // Voice picker
  const [voices, setVoices] = useState(null);
  const [voicesLoading, setVoicesLoading] = useState(false);

  useEffect(() => {
    loadWorlds();
  }, []);

  const loadWorlds = () => {
    setLoading(true);
    apiFetch('/worlds/')
      .then(setWorlds)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  const loadVoices = () => {
    if (voices) return;
    setVoicesLoading(true);
    apiFetch('/stories/voices')
      .then(setVoices)
      .catch(() => {})
      .finally(() => setVoicesLoading(false));
  };

  const addCharacter = () => {
    setCharacters([...characters, { name: '', description: '' }]);
  };

  const removeCharacter = (index) => {
    setCharacters(characters.filter((_, i) => i !== index));
  };

  const updateCharacter = (index, field, value) => {
    const updated = [...characters];
    updated[index] = { ...updated[index], [field]: value };
    setCharacters(updated);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('World name is required.');
      return;
    }
    setError(null);
    setCreating(true);
    try {
      const charsObj = {};
      const speakers = [];
      characters.forEach((c) => {
        if (c.name.trim()) {
          const key = c.name.trim().toUpperCase();
          charsObj[key] = c.description;
          speakers.push(key);
        }
      });

      // Build voice config only for characters that have a voice assigned
      const vc = {};
      Object.entries(voiceConfig).forEach(([speaker, config]) => {
        if (config.voice_id) {
          vc[speaker] = config;
        }
      });

      await apiFetch('/worlds/', {
        method: 'POST',
        json: {
          name: name.trim(),
          description: description.trim() || null,
          prompt_template: promptTemplate.trim() || null,
          characters: Object.keys(charsObj).length > 0 ? charsObj : null,
          valid_speakers: speakers.length > 0 ? speakers : null,
          voice_config: Object.keys(vc).length > 0 ? vc : null,
          visibility,
        },
      });

      // Reset form and reload
      setName('');
      setDescription('');
      setPromptTemplate(PLACEHOLDER_TEMPLATE);
      setCharacters([{ name: 'NARRATOR', description: 'Tells the story' }]);
      setVoiceConfig({});
      setVisibility('private');
      setShowCreate(false);
      loadWorlds();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const builtinWorlds = worlds.filter((w) => w.is_builtin);
  const myWorlds = worlds.filter((w) => !w.is_builtin && w.owner_name);
  const publicWorlds = worlds.filter((w) => !w.is_builtin && !w.owner_name);

  return (
    <div className="page-card">
      <div className="page-header">
        <h1>Story Worlds</h1>
        <button className="btn btn-primary" onClick={() => { setShowCreate(!showCreate); loadVoices(); }}>
          {showCreate ? 'Cancel' : 'Create World'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {showCreate && (
        <form onSubmit={handleCreate} className="create-world-form">
          <h2>Create a New World</h2>

          <div className="form-group">
            <label htmlFor="world-name">World Name</label>
            <input
              id="world-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Fairy Tale Forest, Space Explorers..."
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="world-desc">Description</label>
            <textarea
              id="world-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe your world..."
              rows={2}
            />
          </div>

          <div className="form-group">
            <label htmlFor="world-template">
              Prompt Template
              <span className="field-hint" style={{ display: 'block', fontWeight: 'normal' }}>
                Use placeholders: {'{language}'}, {'{theme}'}, {'{plot}'}, {'{num_chapters}'}
              </span>
            </label>
            <textarea
              id="world-template"
              value={promptTemplate}
              onChange={(e) => setPromptTemplate(e.target.value)}
              rows={5}
              className="prompt-preview"
            />
          </div>

          <div className="form-group">
            <label>Characters</label>
            {characters.map((char, i) => (
              <div key={i} className="character-row">
                <input
                  type="text"
                  value={char.name}
                  onChange={(e) => updateCharacter(i, 'name', e.target.value)}
                  placeholder="Name (e.g. HERO)"
                  className="character-name-input"
                />
                <input
                  type="text"
                  value={char.description}
                  onChange={(e) => updateCharacter(i, 'description', e.target.value)}
                  placeholder="Description"
                  className="character-desc-input"
                />
                {/* Voice picker for this character */}
                <select
                  className="character-voice-select"
                  value={voiceConfig[char.name.trim().toUpperCase()]?.voice_id || ''}
                  onChange={(e) => {
                    const key = char.name.trim().toUpperCase();
                    if (e.target.value) {
                      setVoiceConfig({ ...voiceConfig, [key]: { voice_id: e.target.value, stability: 0.5, similarity_boost: 0.75, style: 0.3, use_speaker_boost: true } });
                    } else {
                      const updated = { ...voiceConfig };
                      delete updated[key];
                      setVoiceConfig(updated);
                    }
                  }}
                >
                  <option value="">No voice assigned</option>
                  {voicesLoading && <option disabled>Loading voices...</option>}
                  {voices && voices.map((v) => (
                    <option key={v.voice_id} value={v.voice_id}>{v.name}</option>
                  ))}
                </select>
                {characters.length > 1 && (
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => removeCharacter(i)}>
                    Remove
                  </button>
                )}
              </div>
            ))}
            <button type="button" className="btn btn-ghost btn-sm" onClick={addCharacter}>
              + Add Character
            </button>
          </div>

          <div className="form-group">
            <label htmlFor="world-visibility">Visibility</label>
            <select
              id="world-visibility"
              value={visibility}
              onChange={(e) => setVisibility(e.target.value)}
            >
              <option value="private">Private</option>
              <option value="link_only">Link-only</option>
              <option value="public">Public</option>
            </select>
          </div>

          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={creating}>
              {creating ? 'Creating...' : 'Create World'}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => setShowCreate(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="column-loading">Loading worlds...</p>
      ) : (
        <>
          {builtinWorlds.length > 0 && (
            <div className="worlds-section">
              <h2>Built-in Worlds</h2>
              <div className="worlds-grid">
                {builtinWorlds.map((w) => (
                  <WorldCard key={w.id} world={w} />
                ))}
              </div>
            </div>
          )}

          {myWorlds.length > 0 && (
            <div className="worlds-section">
              <h2>My Worlds</h2>
              <div className="worlds-grid">
                {myWorlds.map((w) => (
                  <WorldCard key={w.id} world={w} />
                ))}
              </div>
            </div>
          )}

          {publicWorlds.length > 0 && (
            <div className="worlds-section">
              <h2>Community Worlds</h2>
              <div className="worlds-grid">
                {publicWorlds.map((w) => (
                  <WorldCard key={w.id} world={w} />
                ))}
              </div>
            </div>
          )}

          {worlds.length === 0 && (
            <div className="empty-state">
              <p>No worlds yet. Create your first world to get started!</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function WorldCard({ world }) {
  return (
    <Link to={`/worlds/${world.id}`} className="world-card">
      <div className="world-card-header">
        <h3 className="world-card-name">{world.name}</h3>
        {world.is_builtin && <span className="status-badge status-completed">Built-in</span>}
        {!world.is_builtin && world.visibility === 'public' && (
          <span className="status-badge status-completed">Public</span>
        )}
      </div>
      {world.description && (
        <p className="world-card-desc">{world.description}</p>
      )}
      <div className="world-card-meta">
        <span>{world.story_count} {world.story_count === 1 ? 'story' : 'stories'}</span>
        {world.owner_name && <span>by {world.owner_name}</span>}
      </div>
    </Link>
  );
}
