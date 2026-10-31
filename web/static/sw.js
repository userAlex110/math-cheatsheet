/* 离线缓存：页面 network-first，静态资源 cache-first */
const V = "__VERSION__";
const CACHE = "sx-" + V;
const CORE = [
  "/",
  "/assets/style.css?v=" + V,
  "/assets/app.js?v=" + V,
  "/assets/search.json",
  "/assets/katex/katex.min.css",
  "/manifest.webmanifest",
  "/assets/icon-192.png",
  "/assets/icon-512.png",
];
const FONTS = __FONTS__;

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      await Promise.all(CORE.map((url) => cache.add(url).catch(() => {})));
      await Promise.all(FONTS.map((url) => cache.add(url).catch(() => {})));
      await self.skipWaiting();
    })()
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => k.indexOf("sx-") === 0 && k !== CACHE).map((k) => caches.delete(k)));
      await self.clients.claim();
    })()
  );
});

function networkFirst(request, fallbackKey) {
  return new Promise((resolve) => {
    const timer = setTimeout(async () => {
      const hit = await caches.match(fallbackKey);
      if (hit) resolve(hit);
    }, 3500);

    fetch(request)
      .then((response) => {
        clearTimeout(timer);
        if (response && response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(fallbackKey, copy));
        }
        resolve(response);
      })
      .catch(async () => {
        clearTimeout(timer);
        const hit = await caches.match(fallbackKey);
        resolve(hit || Response.error());
      });
  });
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(networkFirst(request, "/"));
    return;
  }

  if (url.pathname === "/assets/search.json") {
    event.respondWith(networkFirst(request, request));
    return;
  }

  event.respondWith(
    (async () => {
      const hit = await caches.match(request);
      if (hit) return hit;
      const response = await fetch(request);
      if (response.ok && response.type === "basic") {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(request, copy));
      }
      return response;
    })()
  );
});
