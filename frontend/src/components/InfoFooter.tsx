import { useState, useMemo, type ReactNode } from 'react';

const CONTACT_EMAIL = import.meta.env.VITE_CONTACT_EMAIL || 'lingolou@lingolou.app';

/** Render email as separate spans so it doesn't appear as a single scraped string. */
function ObfuscatedEmail() {
  const [user, domain] = useMemo(() => CONTACT_EMAIL.split('@'), []);
  return (
    <a href={`mailto:${user}\u0040${domain}`} onClick={(e) => {
      e.preventDefault();
      window.location.href = `mailto:${user}@${domain}`;
    }}>
      <span>{user}</span>
      <span>{'@'}</span>
      <span>{domain}</span>
    </a>
  );
}

interface InfoSection {
  label: string;
  content: ReactNode;
}

const INFO_SECTIONS: Record<string, InfoSection> = {
  about: {
    label: 'About Lingolou',
    content: (
      <>
        <p>
          Lingolou is developed by two nerd parents for personal use, and we are letting others use it, starting with our friends. The story of lingolou is that
	  we want to teach out kids our native languages (Mama speaks Farsi, Papa speaks Gernam, and our household language is English).
          We realized that our kids remember what they listen to (we have tonies) word by word, They love to listen to the same thing over and over. 
          so why not have them learn the language as well while listening. For mama it has been really hard to find interesting Farsi content online, and 
          hence, this mama started to build Lingolou. The code base was vibe coded, so papa acted as a code reviewer and proper engineer to patch up a solid service.
          We are letting this tool be available online. We are not monitizing it. We primarily want to focus on the community creating content that can be used for all.
	</p>
        <p>
          How this works primarily, is that we allow the user to make a script (with ChatGPT, but you can edit everything). We then use Elevenlabs to 
	  turn that into speech, with amazing voices. After doing this a few times, we  automated all this, and now you can do it too. 
	  The stories are generated based on worlds (i.e Winnie the Pooh, or your own kids' worlds, or their favorite shows). Your content can be private.
	  The default approach is that you generate a story in a world, (you can specify the plot), and the story introduces a character which speaks the target language
	  of your choice. Throughout the story this new character and the other characters in the world learn aspects of target language. The default prompt is provided
	  but you can also adjust the prompt.	  
        </p>
        <p>
          Lingolou supports all languages that elevenLabs support (35+ languages so far). We let you fully customize your stories line by line, prompt by prompt, voice by voice, 
	  and if you share your conent publicly or to your followed (hopefully we can follow you!!), we will have an increasing number of stories to play for our kids. 
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
          Every account gets 20 free stories and 5 free audio generation with our own funded API keys. After that, you can bring
          your own OpenAI and ElevenLabs API keys to generate unlimited stories at your own cost.
        </dd>
        <dt>What languages are supported?</dt>
        <dd>
          We support 35+ languages including Arabic, Mandarin, Spanish, French, Persian, Hindi,
          Japanese, Korean, German, and many more. Check the language selector above for the full list.
        </dd>
        <dt>How does story generation work?</dt>
        <dd>
          You describe a story scenario and characters. GPT-4 writes an emotion-tagged script with
          bilingual dialogue. You can review and edit everything. ElevenLabs then converts each line into natural-sounding speech with
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
	<dt>Are there any rules?</dt>
	<dd>
	    Yes! (1)have to fully supervise the content and take responsibility for the generated content. We do not take any responsibility about the content.
	    (2) We don't approve of political/religious/age-inappropriate/audio-aggressive uses of this work whatsoever. Such content will be taken down without 
	     notice and drastic actions (deletion of account without notice and more) may follow. We allow stories to be "reported", and will moderate them. (3)
            We have released the github repo for this package. 
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
            href="https://github.com/narges-rzv/Lingolou"
            target="_blank"
            rel="noopener noreferrer"
            className="info-github-link"

          >
            github.com/narges-rzv/Lingolou
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
            href="https://github.com/narges-rzv/Lingolou/issues"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub Issues
          </a>
          {' '}or reach out by email at{' '}
          <ObfuscatedEmail />.
        </p>
      </>
    ),
  },
};

export default function InfoFooter() {
  const [openSection, setOpenSection] = useState<string | null>(null);

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
