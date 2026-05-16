import { Marked } from 'marked';
import hljs from 'highlight.js';

// ---------------------------------------------------------------------------
// DOMPurify -- inline minimal sanitizer (no external dependency required)
// ---------------------------------------------------------------------------
// This strips dangerous HTML while preserving safe markup needed for markdown
// rendering. It is intentionally lightweight: no DOM parser dependency, just
// regex-based tag stripping with an allowlist.

const ALLOWED_TAGS = new Set([
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'p', 'br', 'hr',
  'ul', 'ol', 'li',
  'blockquote', 'pre', 'code',
  'strong', 'em', 'del', 'ins', 'sub', 'sup',
  'a', 'img',
  'table', 'thead', 'tbody', 'tr', 'th', 'td',
  'span', 'div',
  'details', 'summary',
]);

const ALLOWED_ATTRS = {
  a: ['href', 'title', 'target', 'rel'],
  img: ['src', 'alt', 'title', 'width', 'height'],
  code: ['class', 'language'],
  pre: ['class'],
  span: ['class'],
  td: ['align'],
  th: ['align'],
};

const ATTR_PATTERN = /(\s+(?:[\w-]+)(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>"']+))?)/gi;
const TAG_OPEN_PATTERN = /<(\w+)((?:\s+[\w-]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>"']+))?)*)\s*>/gi;
const TAG_CLOSE_PATTERN = /<\/(\w+)\s*>/gi;

function sanitizeHtml(html) {
  // Remove script/style blocks entirely
  let clean = html.replace(/<script[\s\S]*?<\/script>/gi, '');
  clean = clean.replace(/<style[\s\S]*?<\/style>/gi, '');

  // Filter opening tags
  clean = clean.replace(TAG_OPEN_PATTERN, (match, tag, attrStr) => {
    if (!ALLOWED_TAGS.has(tag.toLowerCase())) return '';

    const allowedForTag = ALLOWED_ATTRS[tag.toLowerCase()] || [];
    if (!allowedForTag.length) return `<${tag}>`;

    // Parse and filter attributes
    const attrs = [];
    let m;
    const localPattern = /([\w-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>"']+)))?/gi;
    while ((m = localPattern.exec(attrStr)) !== null) {
      const name = m[1].toLowerCase();
      if (!allowedForTag.includes(name)) continue;

      const value = m[2] ?? m[3] ?? m[4] ?? '';
      // Block javascript: URLs in href/src
      if ((name === 'href' || name === 'src') && /^\s*javascript:/i.test(value)) continue;

      attrs.push(`${name}="${value.replace(/"/g, '&quot;')}"`);
    }

    return `<${tag}${attrs.length ? ' ' : ''}${attrs.join(' ')}>`;
  });

  // Filter closing tags
  clean = clean.replace(TAG_CLOSE_PATTERN, (match, tag) => {
    return ALLOWED_TAGS.has(tag.toLowerCase()) ? match : '';
  });

  return clean;
}

// ---------------------------------------------------------------------------
// Marked configuration
// ---------------------------------------------------------------------------

const marked = new Marked({
  gfm: true,
  breaks: true,

  renderer: {
    code({ text, lang }) {
      const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
      let highlighted;
      try {
        highlighted = hljs.highlight(text, { language }).value;
      } catch {
        highlighted = hljs.highlightAuto(text).value;
      }

      return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`;
    },

    link({ href, title, text }) {
      const safeHref = href && /^\s*javascript:/i.test(href) ? '#' : href;
      const titleAttr = title ? ` title="${title.replace(/"/g, '&quot;')}"` : '';
      return `<a href="${safeHref}"${titleAttr} target="_blank" rel="noopener noreferrer">${text}</a>`;
    },

    image({ href, title, text }) {
      const safeHref = href && /^\s*javascript:/i.test(href) ? '' : href;
      const titleAttr = title ? ` title="${title.replace(/"/g, '&quot;')}"` : '';
      const altAttr = text ? ` alt="${text}"` : '';
      return `<img src="${safeHref}"${altAttr}${titleAttr} loading="lazy" />`;
    },
  },
});

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Render a markdown string to sanitised HTML.
 *
 * @param {string} text - Raw markdown content
 * @returns {string} Sanitised HTML ready for dangerouslySetInnerHTML
 */
export function renderMarkdown(text) {
  if (!text) return '';

  const raw = marked.parse(text);
  // Marked may return a Promise when async extensions are present; handle both
  if (typeof raw === 'string') {
    return sanitizeHtml(raw);
  }
  // Synchronous path is guaranteed with our config, but be safe
  return sanitizeHtml(String(raw));
}

/**
 * Render a code string with highlight.js syntax highlighting.
 *
 * @param {string} code    - Source code to highlight
 * @param {string} lang    - Language identifier (e.g. 'python', 'javascript')
 * @returns {string} Highlighted HTML wrapped in <pre><code>
 */
export function renderCode(code, lang) {
  if (!code) return '';

  const language = lang && hljs.getLanguage(lang) ? lang : undefined;

  let highlighted;
  if (language) {
    highlighted = hljs.highlight(code, { language }).value;
  } else {
    highlighted = hljs.highlightAuto(code).value;
  }

  const langClass = language ? ` language-${language}` : '';
  return `<pre><code class="hljs${langClass}">${highlighted}</code></pre>`;
}

export { sanitizeHtml };
export default { renderMarkdown, renderCode, sanitizeHtml };