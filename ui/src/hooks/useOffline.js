import { useState, useCallback, useEffect, useRef } from 'react';

/**
 * Offline detection and action queue hook.
 *
 * Detects navigator.onLine status changes and provides a queue for
 * deferring API calls while offline. Queued actions are replayed
 * automatically when connectivity is restored.
 *
 * @param {object} options
 * @param {number} options.maxQueueSize  - Maximum queued actions (default 100)
 * @param {function} options.onOnline    - Called when going online
 * @param {function} options.onOffline   - Called when going offline
 *
 * @returns {{ isOnline, pendingCount, queueAction, flushQueue, clearQueue }}
 */
export function useOffline(options = {}) {
  const { maxQueueSize = 100, onOnline, onOffline } = options;

  const [isOnline, setIsOnline] = useState(() => {
    if (typeof navigator !== 'undefined') return navigator.onLine;
    return true;
  });
  const [pendingCount, setPendingCount] = useState(0);

  const queueRef = useRef([]);
  const flushingRef = useRef(false);
  const onOnlineRef = useRef(onOnline);
  const onOfflineRef = useRef(onOffline);

  useEffect(() => { onOnlineRef.current = onOnline; }, [onOnline]);
  useEffect(() => { onOfflineRef.current = onOffline; }, [onOffline]);

  const updatePendingCount = useCallback(() => {
    setPendingCount(queueRef.current.length);
  }, []);

  /**
   * Attempt to replay all queued actions in order.
   * Each action is retried up to 3 times before being discarded.
   */
  const flushQueue = useCallback(async () => {
    if (flushingRef.current || queueRef.current.length === 0) return;

    flushingRef.current = true;

    const queue = queueRef.current;
    queueRef.current = [];
    updatePendingCount();

    const remaining = [];

    for (const entry of queue) {
      let success = false;

      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          const result = await entry.action();
          entry.onSuccess?.(result);
          success = true;
          break;
        } catch (err) {
          if (attempt === 2) {
            entry.onFailure?.(err);
          }
        }
      }

      if (!success) {
        // Re-enqueue failed actions at the back so other actions can proceed
        entry.retryCount = (entry.retryCount || 0) + 1;
        if (entry.retryCount < 3) {
          remaining.push(entry);
        }
        // Otherwise the action has exceeded total retries across flushes; drop it
      }
    }

    if (remaining.length > 0) {
      queueRef.current.push(...remaining);
      updatePendingCount();
    }

    flushingRef.current = false;
  }, [updatePendingCount]);

  /**
   * Queue an action for deferred execution.
   *
   * @param {function} action    - An async function to execute when online
   * @param {object}   callbacks
   * @param {function} callbacks.onSuccess - Called with the action result
   * @param {function} callbacks.onFailure - Called with the error if all retries fail
   * @returns {boolean} true if queued (offline), false if executed immediately (online)
   */
  const queueAction = useCallback((action, callbacks = {}) => {
    if (typeof action !== 'function') {
      throw new TypeError('queueAction expects a function');
    }

    // If online, execute immediately
    if (navigator.onLine) {
      action()
        .then((result) => callbacks.onSuccess?.(result))
        .catch((err) => callbacks.onFailure?.(err));
      return false;
    }

    // Offline -- enqueue if within capacity
    if (queueRef.current.length >= maxQueueSize) {
      const err = new Error('Offline queue is full');
      callbacks.onFailure?.(err);
      return true;
    }

    queueRef.current.push({
      action,
      onSuccess: callbacks.onSuccess,
      onFailure: callbacks.onFailure,
      queuedAt: Date.now(),
      retryCount: 0,
    });

    updatePendingCount();
    return true;
  }, [maxQueueSize, updatePendingCount]);

  /**
   * Remove all pending actions from the queue.
   */
  const clearQueue = useCallback(() => {
    queueRef.current = [];
    updatePendingCount();
  }, [updatePendingCount]);

  // Listen for online/offline events
  useEffect(() => {
    const goOnline = () => {
      setIsOnline(true);
      onOnlineRef.current?.();
      // Auto-flush when coming back online
      flushQueue();
    };

    const goOffline = () => {
      setIsOnline(false);
      onOfflineRef.current?.();
    };

    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);

    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, [flushQueue]);

  return {
    isOnline,
    pendingCount,
    queueAction,
    flushQueue,
    clearQueue,
  };
}

export default useOffline;