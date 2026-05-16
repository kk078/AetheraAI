const DB_NAME = 'aethera-offline';
const DB_VERSION = 1;

const STORES = {
  DRAFTS: 'conversation-drafts',
  PREFERENCES: 'user-preferences',
  CACHE: 'cached-api-responses',
};

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

let dbInstance = null;

/**
 * Open (or create) the IndexedDB database.
 * Resolves to the IDBDatabase instance.
 */
function openDB() {
  if (dbInstance) return Promise.resolve(dbInstance);

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      // Conversation drafts -- keyed by session id
      if (!db.objectStoreNames.contains(STORES.DRAFTS)) {
        const draftsStore = db.createObjectStore(STORES.DRAFTS, { keyPath: 'id' });
        draftsStore.createIndex('updatedAt', 'updatedAt', { unique: false });
      }

      // User preferences -- keyed by preference name
      if (!db.objectStoreNames.contains(STORES.PREFERENCES)) {
        db.createObjectStore(STORES.PREFERENCES, { keyPath: 'key' });
      }

      // Cached API responses -- keyed by URL/endpoint
      if (!db.objectStoreNames.contains(STORES.CACHE)) {
        const cacheStore = db.createObjectStore(STORES.CACHE, { keyPath: 'url' });
        cacheStore.createIndex('expiresAt', 'expiresAt', { unique: false });
      }
    };

    request.onsuccess = (event) => {
      dbInstance = event.target.result;

      // Handle unexpected close
      dbInstance.onclose = () => { dbInstance = null; };
      dbInstance.onerror = () => { dbInstance = null; };

      resolve(dbInstance);
    };

    request.onerror = (event) => {
      reject(new Error(`Failed to open IndexedDB: ${event.target.error?.message}`));
    };
  });
}

/**
 * Run a transaction on the given store in the given mode.
 * Returns the object store.
 */
async function getStore(storeName, mode = 'readonly') {
  const db = await openDB();
  const tx = db.transaction(storeName, mode);
  return tx.objectStore(storeName);
}

/**
 * Wrap an IDBRequest in a promise.
 */
function requestToPromise(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Retrieve a value from a store by key.
 *
 * @param {string} storeName - One of STORES values
 * @param {string} key       - The primary key to look up
 * @returns {Promise<any|null>} The stored record, or null if not found
 */
export async function get(storeName, key) {
  const store = await getStore(storeName, 'readonly');
  const request = store.get(key);
  const result = await requestToPromise(request);
  return result ?? null;
}

/**
 * Store a value. The record must include the keyPath field.
 *
 * @param {string} storeName - One of STORES values
 * @param {object} value     - Record to store (must contain keyPath field)
 * @returns {Promise<void>}
 */
export async function set(storeName, value) {
  const store = await getStore(storeName, 'readwrite');
  const request = store.put(value);
  await requestToPromise(request);
}

/**
 * Delete a record by key.
 *
 * @param {string} storeName - One of STORES values
 * @param {string} key       - Primary key to delete
 * @returns {Promise<void>}
 */
export async function deleteEntry(storeName, key) {
  const store = await getStore(storeName, 'readwrite');
  const request = store.delete(key);
  await requestToPromise(request);
}

/**
 * Clear all records from a store.
 *
 * @param {string} storeName - One of STORES values
 * @returns {Promise<void>}
 */
export async function clear(storeName) {
  const store = await getStore(storeName, 'readwrite');
  const request = store.clear();
  await requestToPromise(request);
}

/**
 * Get storage usage statistics.
 *
 * @returns {Promise<{ drafts: number, preferences: number, cache: number, totalBytes: number }>}
 */
export async function getUsage() {
  const db = await openDB();

  const countStore = async (name) => {
    const tx = db.transaction(name, 'readonly');
    const store = tx.objectStore(name);
    return new Promise((resolve) => {
      const req = store.count();
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(0);
    });
  };

  const [drafts, preferences, cache] = await Promise.all([
    countStore(STORES.DRAFTS),
    countStore(STORES.PREFERENCES),
    countStore(STORES.CACHE),
  ]);

  // Estimate storage size if the Storage API is available
  let totalBytes = 0;
  if (navigator.storage && navigator.storage.estimate) {
    try {
      const estimate = await navigator.storage.estimate();
      totalBytes = estimate.usage || 0;
    } catch {
      // Storage estimate not available
    }
  }

  return { drafts, preferences, cache, totalBytes };
}

/**
 * Retrieve all records from a store.
 *
 * @param {string} storeName - One of STORES values
 * @returns {Promise<Array>}
 */
export async function getAll(storeName) {
  const store = await getStore(storeName, 'readonly');
  const request = store.getAll();
  return requestToPromise(request);
}

/**
 * Purge expired cache entries.
 *
 * @returns {Promise<number>} Number of entries removed
 */
export async function purgeExpiredCache() {
  const db = await openDB();
  const now = Date.now();
  let removed = 0;

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORES.CACHE, 'readwrite');
    const store = tx.objectStore(STORES.CACHE);
    const index = store.index('expiresAt');
    const range = IDBKeyRange.upperBound(now);

    const request = index.openCursor(range);
    request.onsuccess = (event) => {
      const cursor = event.target.result;
      if (cursor) {
        cursor.delete();
        removed++;
        cursor.continue();
      }
    };

    tx.oncomplete = () => resolve(removed);
    tx.onerror = () => reject(tx.error);
  });
}

/**
 * Close the database connection.
 */
export function closeDB() {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }
}

export { STORES };
export default { get, set, delete: deleteEntry, clear, getUsage, getAll, purgeExpiredCache, closeDB, STORES };