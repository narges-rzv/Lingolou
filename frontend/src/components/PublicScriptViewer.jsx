import { useState, useEffect } from 'react';
import { publicApiFetch } from '../api';

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

function ScriptEntry({ entry }) {
  const type = entry.type || '';

  if (type === 'line' || type === 'dialogue' || entry.speaker) {
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

  if (type === 'scene' || type === 'scene_heading') {
    const text = entry.text || entry.description || entry.heading || entry.title || '';
    return <div className="script-entry script-scene">{text}</div>;
  }

  if (type === 'pause') {
    return (
      <div className="script-entry script-pause">
        [pause{entry.seconds ? ` ${entry.seconds}s` : entry.duration ? ` ${entry.duration}s` : ''}]
      </div>
    );
  }

  if (type === 'sfx' || type === 'sound_effect') {
    const text = entry.value || entry.text || entry.description || '';
    return <div className="script-entry script-sfx">SFX: {text}</div>;
  }

  if (type === 'bg' || type === 'music' || type === 'performance' || type === 'end') {
    const text = entry.value || entry.text || '';
    return <div className="script-entry" style={{ color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>[{type}: {text}]</div>;
  }

  if (entry.text) {
    return <div className="script-entry">{entry.text}</div>;
  }

  return null;
}

export default function PublicScriptViewer({ storyId, chapterNumber }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    publicApiFetch(`/public/stories/${storyId}/chapters/${chapterNumber}/script?enhanced=true`)
      .then((data) => {
        const arr = Array.isArray(data)
          ? data
          : data.entries || data.script || data.lines || [];
        setEntries(Array.isArray(arr) ? arr : []);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [storyId, chapterNumber]);

  if (loading) return <div className="script-loading">Loading script...</div>;
  if (error) return <div className="script-loading">{error}</div>;
  if (entries.length === 0) return <div className="script-loading">No script available</div>;

  return (
    <div className="script-viewer">
      {entries.map((entry, idx) => (
        <ScriptEntry key={idx} entry={entry} />
      ))}
    </div>
  );
}
