import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { apiFetch } from '../api';
import { LANGUAGES } from '../languages';

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

export default function EditStory() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [prompt, setPrompt] = useState('');
  const [numChapters, setNumChapters] = useState(3);
  const [language, setLanguage] = useState('Persian (Farsi)');
  const [themeKey, setThemeKey] = useState('greetings');
  const [customTheme, setCustomTheme] = useState('');
  const [plot, setPlot] = useState('');
  const [useBuilder, setUseBuilder] = useState(false);

  useEffect(() => {
    apiFetch(`/stories/${id}`)
      .then((data) => {
        setStory(data);
        setTitle(data.title);
        setDescription(data.description || '');
        setPrompt(data.prompt || '');
        setNumChapters(data.chapters?.length || 3);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  const themeText = themeKey === 'custom'
    ? customTheme
    : THEMES.find((t) => t.value === themeKey)?.label || themeKey;

  const applyBuilder = () => {
    if (plot.trim()) {
      setPrompt(buildPrompt(language, themeText, plot, numChapters));
    }
  };

  // Update prompt when builder fields change
  useEffect(() => {
    if (useBuilder && plot.trim()) {
      setPrompt(buildPrompt(language, themeText, plot, numChapters));
    }
  }, [useBuilder, language, themeText, plot, numChapters]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) {
      setError('Prompt is required.');
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      // Update story metadata
      await apiFetch(`/stories/${id}`, {
        method: 'PATCH',
        json: { title, description: description || undefined },
      });

      // Trigger generation
      const data = await apiFetch(`/stories/${id}/generate`, {
        method: 'POST',
        json: {
          title,
          prompt,
          num_chapters: numChapters,
          enhance: true,
        },
      });

      // Navigate back to detail page with the task ID so it shows progress
      navigate(`/stories/${id}`, { state: { taskId: data.task_id, taskType: 'script' } });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="loading">Loading story...</div>;
  if (!story) return <div className="error-message">{error || 'Story not found'}</div>;

  return (
    <div className="page-card">
      <h1>{story.status === 'created' ? 'Generate Story' : 'Edit & Regenerate'}</h1>

      {error && <div className="error-message">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="title">Title</label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
          />
        </div>

        <div className="form-group">
          <label htmlFor="chapters">Chapters</label>
          <select
            id="chapters"
            value={numChapters}
            onChange={(e) => setNumChapters(Number(e.target.value))}
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>

        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => setUseBuilder(!useBuilder)}
          style={{ marginBottom: '1rem' }}
        >
          {useBuilder ? 'Hide' : 'Use'} prompt builder
        </button>

        {useBuilder && (
          <div className="builder-section">
            <div className="form-row">
              <div className="form-group form-group-half">
                <label htmlFor="language">Target Language</label>
                <select
                  id="language"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang} value={lang}>{lang}</option>
                  ))}
                </select>
              </div>
              <div className="form-group form-group-half">
                <label htmlFor="theme">Learning Theme</label>
                <select
                  id="theme"
                  value={themeKey}
                  onChange={(e) => setThemeKey(e.target.value)}
                >
                  {THEMES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
            </div>
            {themeKey === 'custom' && (
              <div className="form-group">
                <input
                  type="text"
                  value={customTheme}
                  onChange={(e) => setCustomTheme(e.target.value)}
                  placeholder="e.g. transportation and vehicles"
                />
              </div>
            )}
            <div className="form-group">
              <label htmlFor="plot">Story Plot</label>
              <textarea
                id="plot"
                value={plot}
                onChange={(e) => setPlot(e.target.value)}
                placeholder="Describe the main plot..."
                rows={3}
              />
            </div>
          </div>
        )}

        <div className="form-group">
          <label htmlFor="prompt">Prompt</label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={10}
            className="prompt-preview"
          />
          <span className="field-hint">
            This is the prompt that will be sent to generate the story. Edit directly or use the builder above.
          </span>
        </div>

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? 'Generating...' : story.status === 'created' ? 'Generate Story' : 'Regenerate Story'}
          </button>
          <Link to={`/stories/${id}`} className="btn btn-ghost">Cancel</Link>
        </div>
      </form>
    </div>
  );
}
