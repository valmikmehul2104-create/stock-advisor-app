// Network-first: hamesha naya page milta hai, internet na ho to purani copy dikhti hai.
const C = "sa-v3";
self.addEventListener("install", e => { self.skipWaiting(); });
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k))))));
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.pathname.startsWith("/api/")) return;
  e.respondWith(fetch(e.request).then(r => {
    // login redirect wali ya error wali response cache nahi karte
    if (r.ok && r.type === "basic" && !r.redirected) { const c = r.clone(); caches.open(C).then(x => x.put(e.request, c)); }
    return r;
  }).catch(() => caches.match(e.request)));
});
