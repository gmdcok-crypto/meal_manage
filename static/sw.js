/**
 * PWA Service Worker (정식 배포용)
 * - /api/* 는 절대 캐시하지 않음 → 로그인/기기 초기화 상태가 서버와 항상 일치
 * - HTML/JS는 네트워크 우선 → 배포 후 사용자가 새 코드를 받도록 함
 * 배포 시 CACHE_NAME 또는 index.html의 sw.js?v= 숫자를 올리면 이전 캐시 정리됨
 */
const CACHE_NAME = 'meal-auth-v1';

self.addEventListener('install', function () {
    self.skipWaiting();
});

self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(keys.map(function (key) {
                if (key !== CACHE_NAME) return caches.delete(key);
            }));
        }).then(function () { return self.clients.claim(); })
    );
});

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    const path = url.pathname;

    // API는 항상 네트워크만 사용 (캐시 금지)
    if (path.startsWith('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    // HTML/JS는 네트워크 우선 → 이전 화면이 남지 않도록 항상 최신으로 로드
    if (event.request.mode === 'navigate' || path === '/' || path === '/index.html' || path.indexOf('app.js') !== -1 || path.indexOf('sw.js') !== -1) {
        event.respondWith(
            fetch(event.request)
                .then(function (res) { return res; })
                .catch(function () { return caches.match(event.request); })
        );
        return;
    }

    event.respondWith(
        caches.match(event.request).then(response => response || fetch(event.request))
    );
});
