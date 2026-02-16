import { useState } from 'react';

const INFO_SECTIONS = {
  about: {
    label: 'About Lingolou',
    content: (
      <>
        <p>
          Lingolou was born from a simple idea: every parent should be able to share bedtime stories
          with their child in any language, even one they don&apos;t speak themselves.
        </p>
        <p>
          We use AI to generate engaging children&apos;s stories with multilingual dialogue, then
          convert them to natural-sounding audio using state-of-the-art text-to-speech. The result
          is a personalized audiobook that introduces your child to a new language through characters
          and situations they love.
        </p>
        <p>
          Lingolou supports 35+ languages, lets you fully customize your stories, and offers a
          community library of public stories you can listen to for free.
        </p>
      </>
    ),
  },
  faq: {
    label: 'FAQ',
    content: (
      <dl className="info-faq-list">
        <dt>Is Lingolou free?</dt>
        <dd>
          Every account gets 3 free stories using our community pool. After that, you can bring
          your own OpenAI and ElevenLabs API keys to generate unlimited stories at your own cost.
        </dd>
        <dt>What languages are supported?</dt>
        <dd>
          We support 35+ languages including Arabic, Mandarin, Spanish, French, Persian, Hindi,
          Japanese, Korean, and many more. Check the language selector above for the full list.
        </dd>
        <dt>How does story generation work?</dt>
        <dd>
          You describe a story scenario and characters. GPT-4 writes an emotion-tagged script with
          bilingual dialogue. ElevenLabs then converts each line into natural-sounding speech with
          the right emotion and accent.
        </dd>
        <dt>Can I edit a story after it&apos;s generated?</dt>
        <dd>
          Yes! You can edit the script, change dialogue, add or remove lines, and regenerate the
          audio for any chapter.
        </dd>
        <dt>Is my data private?</dt>
        <dd>
          Your stories are private by default. You can choose to share them in the public library
          if you like. API keys are encrypted at rest and never shared.
        </dd>
      </dl>
    ),
  },
  github: {
    label: 'GitHub (Open Source)',
    content: (
      <>
        <p>
          Lingolou is fully open source. You can browse the code, report issues, or contribute on GitHub.
        </p>
        <p>
          <a
            href="https://github.com/nargesGh/Lingolou"
            target="_blank"
            rel="noopener noreferrer"
            className="info-github-link"
          >
            github.com/nargesGh/Lingolou
          </a>
        </p>
        <p>
          Contributions, bug reports, and feature requests are welcome. See the README for setup
          instructions and development guidelines.
        </p>
      </>
    ),
  },
  contact: {
    label: 'Contact',
    content: (
      <>
        <p>
          Have a question, suggestion, or just want to say hi? We&apos;d love to hear from you.
        </p>
        <p>
          Open an issue on{' '}
          <a
            href="https://github.com/nargesGh/Lingolou/issues"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub Issues
          </a>
          {' '}or reach out by email at{' '}
          <a href="mailto:hello@lingolou.com">hello@lingolou.com</a>.
        </p>
      </>
    ),
  },
};

export default function InfoFooter() {
  const [openSection, setOpenSection] = useState(null);

  return (
    <footer className="info-footer">
      <nav className="info-links">
        {Object.entries(INFO_SECTIONS).map(([key, { label }]) => (
          <button
            key={key}
            className={`info-link${openSection === key ? ' info-link-active' : ''}`}
            onClick={() => setOpenSection(openSection === key ? null : key)}
          >
            {label}
          </button>
        ))}
      </nav>
      {openSection && (
        <div className="info-panel">
          <div className="info-panel-header">
            <h3>{INFO_SECTIONS[openSection].label}</h3>
            <button
              className="info-panel-close"
              onClick={() => setOpenSection(null)}
              aria-label="Close"
            >
              &times;
            </button>
          </div>
          <div className="info-panel-body">
            {INFO_SECTIONS[openSection].content}
          </div>
        </div>
      )}
    </footer>
  );
}
