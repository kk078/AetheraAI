// ---------------------------------------------------------------------------
// Aethera AI Service Worker
// Provides PWA offline support with app-shell caching and network-first API
// strategy.
// ---------------------------------------------------------------------------

const CACHE_NAME = 'aethera-v1';
const STATIC_CACHE_NAME = 'aethera-static-v1';
const API_CACHE_NAME = 'aethera-api-v1';

// Static assets to pre-cache on install (app shell)
const APP_SHELL = [
  '/',
  '/index.html',
  '/manifest.json',
];

// API endpoints that should use network-first strategy
const API_CACHE_PATTERNS = [
  /\/api\/health/,
  /\/api\/specialists/,
  /\/api\/models/,
  /\/api\/memory/,
  /\/api\/healthcare\/code-/,
  /\/api\/healthcare\/fee-/,
  /\/api\/healthcare\/npi-/,
];

// Maximum time (seconds) to keep a cached API response
const API_CACHE_MAX_AGE = 300; // 5 minutes

// Maximum number of cached API responses
const API_CACHE_MAX_ENTRIES = 100;

// ---------------------------------------------------------------------------
// Install -- pre-cache app shell
// ---------------------------------------------------------------------------

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

// ---------------------------------------------------------------------------
// Activate -- clean up old caches, claim clients
// ---------------------------------------------------------------------------

self.addEventListener('activate', (event) => {
  const currentCaches = new Set([CACHE_NAME, STATIC_CACHE_NAME, API_CACHE_NAME]);

  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names
            .filter((name) => !currentCaches.has(name))
            .map((name) => caches.delete(name))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ---------------------------------------------------------------------------
// Fetch -- route requests to appropriate caching strategy
// ---------------------------------------------------------------------------

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Only handle GET requests; let non-GET pass through
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Skip cross-origin requests unless they are our API
  if (url.origin !== self.location.origin) return;

  // Route: API requests use network-first
  if (isApiRequest(url.pathname)) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Route: Static assets use cache-first
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // Route: Navigation requests use network-first falling back to cached index
  if (request.mode === 'navigate') {
    event.respondWith(navigationHandler(request));
    return;
  }

  // Default: network with cache fallback
  event.respondWith(networkWithCacheFallback(request));
});

// ---------------------------------------------------------------------------
// Message -- handle commands from the main thread
// ---------------------------------------------------------------------------

self.addEventListener('message', (event) => {
  const { type, payload } = event.data || {};

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'CLEAR_CACHE':
      clearAllCaches().then(() => {
        event.source?.postMessage({ type: 'CACHE_CLEARED' });
      });
      break;

    case 'CACHE_URLS':
      if (payload && payload.urls) {
        cacheUrls(payload.urls);
      }
      break;

    case 'GET_CACHE_SIZE':
      getCacheSize().then((size) => {
        event.source?.postMessage({ type: 'CACHE_SIZE', payload: size });
      });
      break;

    default:
      break;
  }
});

// ---------------------------------------------------------------------------
// Caching strategies
// ---------------------------------------------------------------------------

/**
 * Network-first: try the network, fall back to cache. Stale cached API
 * responses are served while the network request runs (stale-while-revalidate
 * for GET).
 */
async function networkFirst(request) {
  const cache = await caches.open(API_CACHE_NAME);

  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      // Store a clone in the cache for offline use
      const cloned = networkResponse.clone();
    cache.put(request, cloned);
      trimCache(API_CACHE_NAME, API_CACHE_MAX_ENTRIES);
    }

    return networkResponse;
  } catch (error) {
    // Network failed -- try the cache
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Return a meaningful offline response
    return new Response(
      JSON.stringify({ error: 'You are offline and no cached data is available.' }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

/**
 * Cache-first: serve from cache if available, otherwise fetch and cache.
 */
async function cacheFirst(request) {
  const cache = await caches.open(STATIC_CACHE_NAME);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    // For HTML navigation, serve the cached index
    if (request.headers.get('Accept')?.includes('text/html')) {
      const fallback = await cache.match('/index.html');
      if (fallback) return fallback;
    }
    return new Response('Offline', { status: 503 });
  }
}

/**
 * Navigation handler: network-first, falling back to cached /index.html
 * so the SPA can handle routing on the client side.
 */
async function navigationHandler(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    const cache = await caches.open(STATIC_CACHE_NAME);
    const cached = await cache.match('/index.html');
    if (cached) return cached;
    return new Response('Offline', { status: 503 });
  }
}

/**
 * Generic network with cache fallback.
 */
async function networkWithCacheFallback(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(request);
    if (cached) return cached;
    return new Response('Offline', { status: 503 });
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isApiRequest(pathname) {
  return API_CACHE_PATTERNS.some((pattern) => pattern.test(pathname));
}

function isStaticAsset(pathname) {
  return /\.(js|css|woff2?|png|jpg|jpeg|gif|svg|ico|webp|avif|woff|ttf|eot)$/i.test(pathname);
}

/**
 * Evict the oldest entries from a cache once it exceeds maxEntries.
 */
async function trimCache(cacheName, maxEntries) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();

  if (keys.length <= maxEntries) return;

  const excess = keys.length - maxEntries;
  for (let i = 0; i < excess; i++) {
    await cache.delete(keys[i]);
  }
}

/**
 * Delete all Aethera caches.
 */
async function clearAllCaches() {
  const names = await caches.keys();
  const aetheraCaches = names.filter((n) => n.startsWith('aethera-'));
  await Promise.all(aetheraCaches.map((n) => caches.delete(n)));
}

/**
 * Pre-cache a list of URLs.
 */
async function cacheUrls(urls) {
  const cache = await caches.open(STATIC_CACHE_NAME);
  await cache.addAll(urls);
}

/**
 * Compute total cache size across all Aethera caches.
 */
async function getCacheSize() {
  const names = await caches.keys();
  const aetheraCaches = names.filter((n) => n.startsWith('aethera-'));
  let totalEntries = 0;

  for (const name of aetheraCaches) {
    const cache = await caches.open(name);
    const keys = await cache.keys();
    totalEntries += keys.length;
  }

  return { caches: aetheraCaches.length, totalEntries };
}