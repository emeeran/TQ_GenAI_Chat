// TQ GenAI Chat Service Worker
// Version 1.0.0

const CACHE_NAME = 'tq-chat-v1.0.0';
const STATIC_CACHE = 'tq-chat-static-v1.0.0';
const DYNAMIC_CACHE = 'tq-chat-dynamic-v1.0.0';

// Resources to cache on install
const STATIC_ASSETS = [
    '/',
    '/static/styles.css',
    '/static/script.js',
    '/static/portrait-sketch-simple.svg',
    '/static/favicon.ico',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js'
];

// Routes that should always be served from network first
const NETWORK_FIRST_ROUTES = [
    '/chat',
    '/upload',
    '/get_models',
    '/save_chat',
    '/documents'
];

// Routes that can be cached
const CACHE_FIRST_ROUTES = [
    '/static/',
    'https://cdn.jsdelivr.net',
    'https://cdnjs.cloudflare.com'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('Service Worker: Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('Service Worker: Installation complete');
                return self.skipWaiting();
            })
            .catch(err => {
                console.error('Service Worker: Installation failed', err);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(cacheName => {
                            return cacheName.startsWith('tq-chat-') && 
                                   cacheName !== STATIC_CACHE && 
                                   cacheName !== DYNAMIC_CACHE;
                        })
                        .map(cacheName => {
                            console.log('Service Worker: Deleting old cache', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            })
            .then(() => {
                console.log('Service Worker: Activation complete');
                return self.clients.claim();
            })
    );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Skip Chrome extension requests
    if (url.protocol === 'chrome-extension:') {
        return;
    }

    event.respondWith(handleFetch(request));
});

async function handleFetch(request) {
    const url = new URL(request.url);
    
    try {
        // Network first for API routes
        if (NETWORK_FIRST_ROUTES.some(route => url.pathname.startsWith(route))) {
            return await networkFirst(request);
        }
        
        // Cache first for static assets
        if (CACHE_FIRST_ROUTES.some(route => url.href.includes(route))) {
            return await cacheFirst(request);
        }
        
        // Stale while revalidate for everything else
        return await staleWhileRevalidate(request);
        
    } catch (error) {
        console.error('Service Worker: Fetch failed', error);
        
        // Return offline fallback if available
        if (url.pathname === '/' || url.pathname.startsWith('/chat')) {
            return await getOfflineFallback();
        }
        
        throw error;
    }
}

// Network first strategy - good for API calls
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.status === 200) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        // Fallback to cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        throw error;
    }
}

// Cache first strategy - good for static assets
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.status === 200) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        throw error;
    }
}

// Stale while revalidate - good for pages
async function staleWhileRevalidate(request) {
    const cache = await caches.open(DYNAMIC_CACHE);
    const cachedResponse = await cache.match(request);
    
    // Start network request in background
    const networkPromise = fetch(request)
        .then(networkResponse => {
            if (networkResponse.status === 200) {
                cache.put(request, networkResponse.clone());
            }
            return networkResponse;
        })
        .catch(err => {
            console.warn('Service Worker: Network request failed', err);
        });
    
    // Return cached version immediately if available
    if (cachedResponse) {
        return cachedResponse;
    }
    
    // Otherwise wait for network
    return networkPromise;
}

// Offline fallback
async function getOfflineFallback() {
    const cache = await caches.open(STATIC_CACHE);
    return cache.match('/') || new Response(
        `<!DOCTYPE html>
        <html>
        <head>
            <title>TQ Chat - Offline</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { 
                    font-family: system-ui; 
                    text-align: center; 
                    padding: 2rem;
                    background: #f5f5f5;
                    color: #333;
                }
                .offline-container {
                    max-width: 400px;
                    margin: 2rem auto;
                    padding: 2rem;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .icon {
                    font-size: 3rem;
                    margin-bottom: 1rem;
                }
                button {
                    background: #2196f3;
                    color: white;
                    border: none;
                    padding: 0.75rem 1.5rem;
                    border-radius: 4px;
                    cursor: pointer;
                    margin-top: 1rem;
                }
            </style>
        </head>
        <body>
            <div class="offline-container">
                <div class="icon">📱</div>
                <h1>You're Offline</h1>
                <p>TQ Chat requires an internet connection to function. Please check your connection and try again.</p>
                <button onclick="window.location.reload()">Retry</button>
            </div>
        </body>
        </html>`,
        {
            headers: { 'Content-Type': 'text/html' }
        }
    );
}

// Background sync for chat messages (when supported)
self.addEventListener('sync', event => {
    if (event.tag === 'background-chat-sync') {
        event.waitUntil(syncPendingChats());
    }
});

async function syncPendingChats() {
    try {
        // Get pending chats from IndexedDB (implementation would depend on your storage strategy)
        console.log('Service Worker: Syncing pending chats...');
        
        // This is a placeholder - you'd implement actual sync logic here
        // For example, sending queued messages that failed to send while offline
        
    } catch (error) {
        console.error('Service Worker: Chat sync failed', error);
    }
}

// Push notification handling (for future implementation)
self.addEventListener('push', event => {
    if (event.data) {
        const data = event.data.json();
        
        const options = {
            body: data.body || 'New message received',
            icon: '/static/portrait-sketch-simple.svg',
            badge: '/static/favicon.ico',
            vibrate: [200, 100, 200],
            data: {
                url: data.url || '/'
            },
            actions: [
                {
                    action: 'open',
                    title: 'Open Chat',
                    icon: '/static/portrait-sketch-simple.svg'
                },
                {
                    action: 'dismiss',
                    title: 'Dismiss'
                }
            ]
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title || 'TQ Chat', options)
        );
    }
});

// Notification click handling
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    if (event.action === 'open' || !event.action) {
        const url = event.notification.data?.url || '/';
        
        event.waitUntil(
            clients.matchAll({ type: 'window' }).then(clientList => {
                // Check if app is already open
                for (const client of clientList) {
                    if (client.url === url && 'focus' in client) {
                        return client.focus();
                    }
                }
                
                // Open new window if not already open
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
        );
    }
});

// Message handling for communication with main thread
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('Service Worker: Loaded successfully');
