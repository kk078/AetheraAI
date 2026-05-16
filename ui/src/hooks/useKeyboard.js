import { useCallback, useEffect, useRef } from 'react';

/**
 * Keyboard shortcuts hook.
 *
 * Built-in shortcuts:
 *   Ctrl+K / Cmd+K   - Open command palette
 *   Ctrl+N / Cmd+N   - New chat
 *   Escape           - Close active panel / overlay
 *   Ctrl+/ / Cmd+/   - Toggle help
 *
 * Custom shortcuts can be registered and unregistered at runtime.
 *
 * @returns {{ registerShortcut, unregisterShortcut }}
 */
export function useKeyboard(options = {}) {
  const { onCommandPalette, onNewChat, onEscape, onHelp } = options;

  // Registry of custom shortcuts keyed by a unique id
  const shortcutsRef = useRef(new Map());
  const idCounterRef = useRef(0);

  // Stable callback refs so the global listener never goes stale
  const onCommandPaletteRef = useRef(onCommandPalette);
  const onNewChatRef = useRef(onNewChat);
  const onEscapeRef = useRef(onEscape);
  const onHelpRef = useRef(onHelp);

  useEffect(() => { onCommandPaletteRef.current = onCommandPalette; }, [onCommandPalette]);
  useEffect(() => { onNewChatRef.current = onNewChat; }, [onNewChat]);
  useEffect(() => { onEscapeRef.current = onEscape; }, [onEscape]);
  useEffect(() => { onHelpRef.current = onHelp; }, [onHelp]);

  /**
   * Normalise a keyboard event into a comparable shortcut string.
   * Format: [Ctrl+][Alt+][Shift+][Meta+]<key>
   * Example: "Ctrl+k", "Escape", "Meta+Shift+p"
   */
  const normaliseCombo = useCallback((event) => {
    const parts = [];
    if (event.ctrlKey || event.metaKey) parts.push('Ctrl');
    if (event.altKey) parts.push('Alt');
    if (event.shiftKey) parts.push('Shift');
    // Use event.key for the final segment, lower-cased for letter keys
    const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
    parts.push(key);
    return parts.join('+');
  }, []);

  const handleKeyDown = useCallback((event) => {
    const combo = normaliseCombo(event);

    // Check custom shortcuts first (later-registered take precedence)
    const customEntries = [...shortcutsRef.current.values()].reverse();
    for (const entry of customEntries) {
      if (entry.combo === combo) {
        event.preventDefault();
        event.stopPropagation();
        entry.handler(event);
        return;
      }
    }

    // Built-in shortcuts
    switch (combo) {
      case 'Ctrl+k':
        event.preventDefault();
        onCommandPaletteRef.current?.();
        break;

      case 'Ctrl+n':
        event.preventDefault();
        onNewChatRef.current?.();
        break;

      case 'Escape':
        onEscapeRef.current?.();
        break;

      case 'Ctrl+/':
        event.preventDefault();
        onHelpRef.current?.();
        break;

      default:
        break;
    }
  }, [normaliseCombo]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown, true);
    return () => window.removeEventListener('keydown', handleKeyDown, true);
  }, [handleKeyDown]);

  /**
   * Register a custom keyboard shortcut.
   *
   * @param {string}   combo   - Shortcut combo string, e.g. "Ctrl+Shift+a"
   * @param {function} handler - Callback receiving the KeyboardEvent
   * @returns {number} id - Opaque id for unregistering
   */
  const registerShortcut = useCallback((combo, handler) => {
    const id = ++idCounterRef.current;
    // Normalise the stored combo to match event normalisation
    const normalised = combo
      .split('+')
      .map((part) => (part.length === 1 ? part.toLowerCase() : part))
      .join('+');
    shortcutsRef.current.set(id, { combo: normalised, handler });
    return id;
  }, []);

  /**
   * Unregister a previously registered shortcut by its id.
   *
   * @param {number} id - The id returned by registerShortcut
   */
  const unregisterShortcut = useCallback((id) => {
    shortcutsRef.current.delete(id);
  }, []);

  return {
    registerShortcut,
    unregisterShortcut,
  };
}

export default useKeyboard;