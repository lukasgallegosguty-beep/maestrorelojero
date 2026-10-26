/* Service worker de Maestro Relojero.
   Permite abrir el juego sin conexión después de la primera visita.
   Cada vez que publiques una versión nueva del juego, cambia VERSION (v1 → v2 …). */
const VERSION = 'v1';
const CACHE = 'relojero-' + VERSION;
const BASICOS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon.svg',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png'
];

self.addEventListener('install', (evento) => {
  evento.waitUntil(
    caches.open(CACHE)
      .then((cache) => Promise.allSettled(BASICOS.map((url) => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((claves) => Promise.all(
        claves.filter((c) => c.startsWith('relojero-') && c !== CACHE).map((c) => caches.delete(c))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (evento) => {
  const pedido = evento.request;
  if (pedido.method !== 'GET' || new URL(pedido.url).origin !== self.location.origin) return;

  const esPagina = pedido.mode === 'navigate' || (pedido.headers.get('accept') || '').includes('text/html');

  if (esPagina) {
    // Páginas: primero la red (para recibir actualizaciones); si no hay conexión, la copia guardada.
    evento.respondWith(
      fetch(pedido)
        .then((respuesta) => {
          const copia = respuesta.clone();
          caches.open(CACHE).then((cache) => cache.put(pedido, copia));
          return respuesta;
        })
        .catch(() => caches.match(pedido).then((r) => r || caches.match('./index.html')))
    );
    return;
  }

  // Resto de archivos: la copia guardada al instante y actualización en segundo plano.
  evento.respondWith(
    caches.match(pedido).then((guardada) => {
      const desdeRed = fetch(pedido)
        .then((respuesta) => {
          if (respuesta && respuesta.ok) {
            const copia = respuesta.clone();
            caches.open(CACHE).then((cache) => cache.put(pedido, copia));
          }
          return respuesta;
        })
        .catch(() => guardada);
      return guardada || desdeRed;
    })
  );
});
