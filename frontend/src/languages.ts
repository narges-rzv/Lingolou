// ElevenLabs v3 supported languages
export const LANGUAGES = [
  'Arabic', 'Bulgarian', 'Chinese (Mandarin)', 'Croatian', 'Czech',
  'Danish', 'Dutch', 'English', 'Filipino', 'Finnish',
  'French', 'German', 'Greek', 'Hebrew', 'Hindi',
  'Hungarian', 'Indonesian', 'Italian', 'Japanese', 'Korean',
  'Malay', 'Norwegian', 'Persian (Farsi)', 'Polish', 'Portuguese',
  'Romanian', 'Russian', 'Slovak', 'Spanish', 'Swedish',
  'Tamil', 'Thai', 'Turkish', 'Ukrainian', 'Vietnamese',
];

/** Sentinel value meaning "show all languages" */
export const ALL_LANGUAGES = '';

export const DEFAULT_LANGUAGE = ALL_LANGUAGES;

/** Flag-inspired accent colors (muted to fit dark theme) */
export const LANGUAGE_COLORS: Record<string, string> = {
  'Arabic': '#2d6a4f',
  'Bulgarian': '#4a7c59',
  'Chinese (Mandarin)': '#c24a4a',
  'Croatian': '#3a5ba0',
  'Czech': '#3a5ba0',
  'Danish': '#c24a4a',
  'Dutch': '#d4762c',
  'English': '#3a5ba0',
  'Filipino': '#3a5ba0',
  'Finnish': '#3a5ba0',
  'French': '#3a5ba0',
  'German': '#c9a227',
  'Greek': '#3a8fbf',
  'Hebrew': '#3a5ba0',
  'Hindi': '#d4762c',
  'Hungarian': '#4a7c59',
  'Indonesian': '#c24a4a',
  'Italian': '#4a7c59',
  'Japanese': '#c24a4a',
  'Korean': '#3a5ba0',
  'Malay': '#c9a227',
  'Norwegian': '#c24a4a',
  'Persian (Farsi)': '#4a7c59',
  'Polish': '#c24a4a',
  'Portuguese': '#4a7c59',
  'Romanian': '#c9a227',
  'Russian': '#3a5ba0',
  'Slovak': '#3a5ba0',
  'Spanish': '#c9a227',
  'Swedish': '#c9a227',
  'Tamil': '#d4762c',
  'Thai': '#3a5ba0',
  'Turkish': '#c24a4a',
  'Ukrainian': '#c9a227',
  'Vietnamese': '#c24a4a',
};
