import { useState, useEffect, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiFetch } from '../api';
import { useLanguage } from '../context/LanguageContext';
import { LANGUAGES } from '../languages';
import BudgetBanner from '../components/BudgetBanner';

const THEMES = [
  { value: 'greetings', label: 'Greetings and introductions' },
  { value: 'colors_numbers', label: 'Colors and numbers' },
  { value: 'animals', label: 'Animals and nature' },
  { value: 'food', label: 'Food and meals' },
  { value: 'family', label: 'Family and friends' },
  { value: 'feelings', label: 'Feelings and emotions' },
  { value: 'daily', label: 'Daily activities and routines' },
  { value: 'weather', label: 'Weather and seasons' },
  { value: 'directions', label: 'Directions and places' },
  { value: 'custom', label: 'Custom...' },
];

function buildPrompt(language, themeText, plot, numChapters) {
  return `Write a story aimed for 4-8 year old kids, which involves the PAW Patrol in a new adventure. They meet a new pup, who speaks a different language (${language} here), and the PAW Patrol learn a bit of basic ${language} by communicating with the new pup, and repeating. Include short repetition of the language lessons, by various characters, to reinforce learning. Start simple. The current theme of the learning is ${themeText} and a few basic nouns, a few basic sentence structures, and basic pronouns. The plot of the story is around ${plot}. Inject some subplots to make it exciting. Keep the story in ${numChapters} chapters. Start with chapter 1. Each chapter should be around 1000 words and all PAW Patrol characters should participate at some stage of the story and bring in their specific expertise. Every time a new word (start with 1-2 word phrases) is introduced in the language, have the other pups or Ryder repeat it a few times, (to reinforce learning). Then repeat with the term in the target language and English (when Ryder explains what they just learned), and then continue. Start with nouns and short phrases within the theme of ${themeText}. Basic short sentences. Add basic adjectives. And then the sentences (2-5 words usually, maybe up to 6-7. Not long).`;
}

export default function NewStory() {
  const navigate = useNavigate();
  const { language: globalLanguage } = useLanguage();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [language, setLanguage] = useState(globalLanguage);
  const [themeKey, setThemeKey] = useState('greetings');
  const [customTheme, setCustomTheme] = useState('');
  const [plot, setPlot] = useState('saving a lost baby penguin, and reuniting her with her parents');
  const [numChapters, setNumChapters] = useState(3);
  const [promptEdited, setPromptEdited] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [voices, setVoices] = useState(null);
  const [voicesLoading, setVoicesLoading] = useState(false);
  const [showVoices, setShowVoices] = useState(false);
  const [voicePreview, setVoicePreview] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [keyStatus, setKeyStatus] = useState(null);

  const themeText = themeKey === 'custom'
    ? customTheme
    : THEMES.find((t) => t.value === themeKey)?.label || themeKey;

  useEffect(() => {
    apiFetch('/auth/api-keys').then(setKeyStatus).catch(() => {});
  }, []);

  // Auto-generate prompt when inputs change (unless user manually edited it)
  const generatedPrompt = useMemo(
    () => buildPrompt(language, themeText, plot, numChapters),
    [language, themeText, plot, numChapters]
  );

  useEffect(() => {
    if (!promptEdited) {
      setPrompt(generatedPrompt);
    }
  }, [generatedPrompt, promptEdited]);

  const handlePromptChange = (e) => {
    setPrompt(e.target.value);
    setPromptEdited(true);
  };

  const handleResetPrompt = () => {
    setPrompt(generatedPrompt);
    setPromptEdited(false);
  };

  const loadVoices = () => {
    if (voices) {
      setShowVoices(!showVoices);
      return;
    }
    setShowVoices(true);
    setVoicesLoading(true);
    apiFetch('/stories/voices')
      .then(setVoices)
      .catch((err) => setError(`Failed to load voices: ${err.message}`))
      .finally(() => setVoicesLoading(false));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!plot.trim()) {
      setError('Please describe the plot of the story.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const story = await apiFetch('/stories/', {
        method: 'POST',
        json: {
          title: title || `${language} Adventure`,
          description: description || `A PAW Patrol ${language} learning story about ${themeText.toLowerCase()}`,
          prompt,
          num_chapters: numChapters,
          language,
          config_override: {
            target_language: { name: language, code: language.slice(0, 2).toLowerCase() },
          },
        },
      });
      navigate(`/stories/${story.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-card">
      <BudgetBanner />
      <h1>Create New Story</h1>

      {keyStatus && (
        <div className="key-status-banner">
          {keyStatus.has_openai_key ? (
            <span className="key-info key-info-own">Using your OpenAI key</span>
          ) : keyStatus.free_stories_used < keyStatus.free_stories_limit ? (
            <span className="key-info key-info-free">
              Using free tier ({keyStatus.free_stories_limit - keyStatus.free_stories_used} of {keyStatus.free_stories_limit} stories remaining)
            </span>
          ) : (
            <span className="key-info key-info-none">
              Free tier used up — <Link to="/settings">add your API key</Link> to continue
            </span>
          )}
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="title">Title</label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={`PAW Patrol Learns ${language}`}
          />
        </div>

        <div className="form-group">
          <label htmlFor="description">Description (optional)</label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="A brief description of your story"
            rows={2}
          />
        </div>

        <div className="form-row">
          <div className="form-group form-group-half">
            <label htmlFor="language">Target Language</label>
            <select
              id="language"
              value={language}
              onChange={(e) => { setLanguage(e.target.value); setPromptEdited(false); }}
            >
              {LANGUAGES.map((lang) => (
                <option key={lang} value={lang}>{lang}</option>
              ))}
            </select>
          </div>

          <div className="form-group form-group-half">
            <label htmlFor="chapters">Chapters</label>
            <select
              id="chapters"
              value={numChapters}
              onChange={(e) => { setNumChapters(Number(e.target.value)); setPromptEdited(false); }}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="theme">Learning Theme</label>
          <select
            id="theme"
            value={themeKey}
            onChange={(e) => { setThemeKey(e.target.value); setPromptEdited(false); }}
          >
            {THEMES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          {themeKey === 'custom' && (
            <input
              type="text"
              value={customTheme}
              onChange={(e) => { setCustomTheme(e.target.value); setPromptEdited(false); }}
              placeholder="e.g. transportation and vehicles"
              style={{ marginTop: '0.5rem' }}
            />
          )}
        </div>

        <div className="form-group">
          <label htmlFor="plot">Story Plot</label>
          <textarea
            id="plot"
            value={plot}
            onChange={(e) => { setPlot(e.target.value); setPromptEdited(false); }}
            placeholder="Describe the main plot of the story..."
            rows={3}
          />
          <span className="field-hint">
            What adventure should the PAW Patrol go on?
          </span>
        </div>

        <div className="form-group">
          <label htmlFor="prompt">
            Generated Prompt
            {promptEdited && (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={handleResetPrompt}
                style={{ marginLeft: '0.5rem', verticalAlign: 'middle' }}
              >
                Reset
              </button>
            )}
          </label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={handlePromptChange}
            rows={8}
            className="prompt-preview"
          />
          <span className="field-hint">
            {promptEdited
              ? 'You edited this prompt manually. Click Reset to regenerate from your selections.'
              : 'Auto-generated from your selections above. You can edit it directly if needed.'}
          </span>
        </div>

        <div className="voices-section">
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={loadVoices}
          >
            {showVoices ? 'Hide' : 'Show'} available voices
          </button>

          {showVoices && (
            <div className="voices-list">
              {voicesLoading && <p className="field-hint">Loading voices from ElevenLabs...</p>}
              {voices && voices.length === 0 && <p className="field-hint">No voices found.</p>}
              {voices && voices.length > 0 && (
                <div className="voices-grid">
                  {voices.map((v) => (
                    <div key={v.voice_id} className="voice-card">
                      <div className="voice-card-header">
                        <span className="voice-name">{v.name}</span>
                        <span className="voice-category">{v.category}</span>
                      </div>
                      {v.labels && Object.keys(v.labels).length > 0 && (
                        <div className="voice-labels">
                          {Object.entries(v.labels).map(([k, val]) => (
                            <span key={k} className="voice-label">{k}: {val}</span>
                          ))}
                        </div>
                      )}
                      {v.preview_url && (
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          onClick={() => {
                            if (voicePreview === v.voice_id) {
                              setVoicePreview(null);
                            } else {
                              setVoicePreview(v.voice_id);
                            }
                          }}
                        >
                          {voicePreview === v.voice_id ? 'Hide preview' : 'Preview'}
                        </button>
                      )}
                      {voicePreview === v.voice_id && v.preview_url && (
                        <audio controls preload="none" src={v.preview_url} className="voice-audio" />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? 'Creating...' : 'Create Story'}
          </button>
          <Link to="/dashboard" className="btn btn-ghost">Cancel</Link>
        </div>
      </form>
    </div>
  );
}
