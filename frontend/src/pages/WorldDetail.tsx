import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { apiFetch } from '../api';
import type { WorldResponse, ShareLinkResponse } from '../types';

export default function WorldDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [world, setWorld] = useState<WorldResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);

  // Edit form state
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editTemplate, setEditTemplate] = useState('');
  const [editVisibility, setEditVisibility] = useState('private');

  useEffect(() => {
    apiFetch(`/worlds/${id}`)
      .then((data: WorldResponse) => {
        setWorld(data);
        setEditName(data.name);
        setEditDescription(data.description || '');
        setEditTemplate(data.prompt_template || '');
        setEditVisibility(data.visibility);
      })
      .catch((err: unknown) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, [id]);

  const isOwner = world && !world.is_builtin && world.owner_name;

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const data = await apiFetch(`/worlds/${id}`, {
        method: 'PATCH',
        json: {
          name: editName,
          description: editDescription || null,
          prompt_template: editTemplate || null,
          visibility: editVisibility,
        },
      }) as WorldResponse;
      setWorld(data);
      setEditing(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await apiFetch(`/worlds/${id}`, { method: 'DELETE' });
      navigate('/worlds');
    } catch (err) {
      setError((err as Error).message);
      setShowDelete(false);
    }
  };

  const handleCopyShareLink = async () => {
    try {
      const data = await apiFetch(`/worlds/${id}/share-link`, { method: 'POST' }) as ShareLinkResponse;
      await navigator.clipboard.writeText(data.share_url);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  if (loading) return <div className="loading">Loading world...</div>;
  if (!world) return <div className="error-message">{error || 'World not found'}</div>;

  return (
    <div className="page-card">
      {editing ? (
        <>
          <h1>Edit World</h1>
          {error && <div className="error-message">{error}</div>}
          <div className="form-group">
            <label htmlFor="edit-name">Name</label>
            <input id="edit-name" type="text" value={editName} onChange={(e) => setEditName(e.target.value)} />
          </div>
          <div className="form-group">
            <label htmlFor="edit-desc">Description</label>
            <textarea id="edit-desc" value={editDescription} onChange={(e) => setEditDescription(e.target.value)} rows={2} />
          </div>
          <div className="form-group">
            <label htmlFor="edit-template">Prompt Template</label>
            <textarea id="edit-template" value={editTemplate} onChange={(e) => setEditTemplate(e.target.value)} rows={5} className="prompt-preview" />
          </div>
          <div className="form-group">
            <label htmlFor="edit-visibility">Visibility</label>
            <select id="edit-visibility" value={editVisibility} onChange={(e) => setEditVisibility(e.target.value)}>
              <option value="private">Private</option>
              <option value="link_only">Link-only</option>
              <option value="public">Public</option>
            </select>
          </div>
          <div className="form-actions">
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button className="btn btn-ghost" onClick={() => setEditing(false)}>Cancel</button>
          </div>
        </>
      ) : (
        <>
          <div className="story-detail-header">
            <div>
              <h1>{world.name}</h1>
              <div className="story-meta">
                {world.is_builtin && <span className="status-badge status-completed">Built-in</span>}
                {world.visibility === 'public' && <span className="status-badge status-completed">Public</span>}
                {world.visibility === 'link_only' && <span className="status-badge status-created">Link-only</span>}
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>
                  {world.story_count} {world.story_count === 1 ? 'story' : 'stories'}
                  {world.owner_name && ` \u00b7 by ${world.owner_name}`}
                </span>
              </div>
              {world.description && (
                <p className="description" style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                  {world.description}
                </p>
              )}
            </div>
          </div>

          {error && <div className="error-message">{error}</div>}

          {/* Characters */}
          {world.characters && Object.keys(world.characters).length > 0 && (
            <div className="world-section">
              <h2 className="section-title">Characters</h2>
              <div className="characters-list">
                {Object.entries(world.characters).map(([name, desc]) => (
                  <div key={name} className="character-item">
                    <strong>{name}</strong>
                    <span style={{ color: 'var(--color-text-secondary)' }}>{desc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Prompt Template */}
          {world.prompt_template && (
            <div className="world-section">
              <h2 className="section-title">Prompt Template</h2>
              <pre className="prompt-preview" style={{ whiteSpace: 'pre-wrap', padding: '1rem', margin: 0 }}>
                {world.prompt_template}
              </pre>
            </div>
          )}

          {/* Voice Config */}
          {world.voice_config && Object.keys(world.voice_config).length > 0 && (
            <div className="world-section">
              <h2 className="section-title">Voice Assignments</h2>
              <div className="characters-list">
                {Object.entries(world.voice_config).map(([speaker, config]) => (
                  <div key={speaker} className="character-item">
                    <strong>{speaker}</strong>
                    <span style={{ color: 'var(--color-text-secondary)', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      {(config as Record<string, unknown>).voice_id as string}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="story-actions">
            <Link to={`/stories/new?world=${world.id}`} className="btn btn-primary">
              Create Story in this World
            </Link>
            {isOwner && (
              <>
                <button className="btn btn-ghost" onClick={() => setEditing(true)}>Edit</button>
                <button className="btn btn-ghost" onClick={handleCopyShareLink}>
                  {copySuccess ? 'Copied!' : 'Copy Share Link'}
                </button>
                <button className="btn btn-danger" onClick={() => setShowDelete(true)}>Delete</button>
              </>
            )}
            <Link to="/worlds" className="btn btn-ghost">Back to Worlds</Link>
          </div>

          {showDelete && (
            <div className="confirm-overlay" onClick={() => setShowDelete(false)}>
              <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
                <p>Delete &quot;{world.name}&quot;? This cannot be undone.</p>
                <div className="confirm-actions">
                  <button className="btn btn-ghost" onClick={() => setShowDelete(false)}>Cancel</button>
                  <button className="btn btn-danger" onClick={handleDelete}>Delete</button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
