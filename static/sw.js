/* 今日待办 Service Worker
 * 策略：
 *  - 页面导航：网络优先，失败回退缓存的应用外壳（弱网/离线也能打开）
 *  - 静态资源：缓存优先，后台更新
 *  - /api/* ：完全不缓存、不拦截（数据必须实时，避免显示过期待办）
 */
const CACHE_NAME = "todo-shell-v1";
const SHELL = [
  "/",
  "/static/manifest.webmanifest",
  "/static/icon-192.png",
  "/static/icon-512.png",
  "/static/apple-touch-icon.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // 只处理同源 GET 请求
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  // 接口一律走网络，绝不缓存
  if (url.pathname.startsWith("/api/")) return;

  // 页面导航：网络优先，离线回退外壳
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put("/", copy));
          return res;
        })
        .catch(() => caches.match("/"))
    );
    return;
  }

  // 静态资源：缓存优先
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(req, copy));
        }
        return res;
      });
    })
  );
});
