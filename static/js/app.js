/* 커스텀 알림: PWA·크롬 동일 스타일, 도메인/내용 라벨 없음 */
function showAlert(message, onConfirm) {
    var overlay = document.getElementById('alert-overlay');
    var msgEl = document.getElementById('alert-message');
    var btn = document.getElementById('alert-confirm');
    if (!overlay || !msgEl || !btn) return;
    msgEl.textContent = message;
    overlay.setAttribute('aria-hidden', 'false');
    var handler = function () {
        btn.onclick = null;
        overlay.setAttribute('aria-hidden', 'true');
        if (typeof onConfirm === 'function') onConfirm();
    };
    btn.onclick = handler;
}

function formatMealAndTime(mealType, authTime) {
    var label = (mealType && { breakfast: '조식', lunch: '중식', dinner: '석식' }[mealType]) || mealType || '';
    return (label + '  ' + (authTime || '')).trim() || '—';
}

const app = {
    state: {
        isLoggedIn: false,
        preChecked: false,
        user: null,
        meal: null,
        lastAuthAt: null   // 마지막 QR 인증 성공 시각 (5분 후 인증화면 다시보기 비표시용)
        , lastAuthMealType: null
        , lastAuthTime: null
    },
    homeClockTimer: null,
    authCountdownTimer: null,

    async init() {
        // 토큰이 있으면 로딩 화면 → 서버 확인 후 홈 또는 로그인 (깜빡임 방지)
        var token = localStorage.getItem('meal_token');
        if (token) {
            this.showPage('page-loading');
            try {
                var res = await fetch('/api/auth/status?_=' + Date.now(), {
                    cache: 'no-store',
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                if (res.ok) {
                    var userStr = localStorage.getItem('meal_user');
                    if (userStr) {
                        this.state.user = JSON.parse(userStr);
                        this.state.isLoggedIn = true;
                        var lastAt = localStorage.getItem('meal_lastAuthAt');
                        this.state.lastAuthAt = lastAt ? parseInt(lastAt, 10) : null;
                        this.state.lastAuthMealType = localStorage.getItem('meal_lastAuthMealType') || null;
                        this.state.lastAuthTime = localStorage.getItem('meal_lastAuthTime') || null;
                        this.updateUserInfoUI();
                        this.showPage('page-home');
                        return;
                    }
                }
                // 401/403만 로그아웃(토큰 삭제). 그 외는 네트워크 재시도 유도
                if (res.status === 401 || res.status === 403) {
                    this.logout();
                    return;
                }
                // 서버 오류 등
                showAlert("서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.", function () { app.showPage('page-login'); });
                return;
            } catch (e) {
                console.error("Auth status check failed:", e);
                showAlert("연결할 수 없습니다. 네트워크를 확인한 뒤 다시 시도해 주세요.", function () { app.showPage('page-login'); });
                return;
            }
        }
        this.showPage('page-login');
    },

    updateUserInfoUI() {
        if (this.state.user) {
            const nameEl = document.getElementById('user-name');
            const deptEl = document.getElementById('user-dept');
            if (nameEl) nameEl.textContent = `${this.state.user.name} 님`;
            if (deptEl) deptEl.textContent = `사번: ${this.state.user.emp_no}`;
        }
    },

    showPage(pageId) {
        if (this.homeClockTimer) {
            clearInterval(this.homeClockTimer);
            this.homeClockTimer = null;
        }
        if (this.authCountdownTimer) {
            clearInterval(this.authCountdownTimer);
            this.authCountdownTimer = null;
        }
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(pageId).classList.add('active');
        if (pageId === 'page-home') {
            this.startHomeClock();
            this.loadNoticeContent();
        }
    },

    startHomeClock() {
        const el = document.getElementById('home-datetime');
        if (!el) return;
        const weekDays = ['일', '월', '화', '수', '목', '금', '토'];
        const update = () => {
            const now = new Date();
            const h = now.getHours();
            const m = now.getMinutes();
            const day = weekDays[now.getDay()];
            el.textContent = String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0') + '(' + day + ')';
        };
        update();
        this.homeClockTimer = setInterval(update, 1000);
    },

    loadNoticeContent() {
        const el = document.getElementById('home-notice-content');
        if (!el) return;
        fetch('notice.html?v=' + Date.now())
            .then(r => r.text())
            .then(html => { el.innerHTML = html.replace(/\n/g, '<br>'); })
            .catch(() => { el.innerHTML = '공지가 없습니다.'; });
    },

    async loginDevice() {
        const empNo = document.getElementById('login-emp-no').value.trim();
        const name = document.getElementById('login-name').value.trim();
        const password = document.getElementById('login-password').value.trim();

        if (!empNo || !name || !password) {
            showAlert("사번, 이름, 초기 비밀번호를 모두 입력해주세요.");
            return;
        }

        try {
            const res = await fetch('/api/auth/verify_device', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ emp_no: empNo, name: name, password: password })
            });

            // JSON 파싱 에러 방지를 위해 텍스트로 먼저 확인
            const text = await res.text();
            let data;
            try {
                data = JSON.parse(text);
            } catch (jsonErr) {
                console.error("JSON parse error. Raw response:", text);
                throw new Error("Invalid server response (not JSON)");
            }

            if (res.ok) {
                localStorage.setItem('meal_token', data.access_token);
                localStorage.setItem('meal_user', JSON.stringify(data.user));
                this.state.isLoggedIn = true;
                this.state.user = data.user;
                this.updateUserInfoUI();

                showAlert("기기 인증이 완료되었습니다. 이제 스캔 버튼을 눌러주세요.", function () { app.showPage('page-home'); });
            } else {
                showAlert(data.detail || "인증에 실패했습니다.");
            }
        } catch (e) {
            showAlert("서버 연결 실패: " + e.message);
        }
    },

    logout() {
        localStorage.removeItem('meal_token');
        localStorage.removeItem('meal_user');
        localStorage.removeItem('meal_lastAuthAt');
        localStorage.removeItem('meal_lastAuthMealType');
        localStorage.removeItem('meal_lastAuthTime');
        this.state.isLoggedIn = false;
        this.state.user = null;
        this.state.lastAuthAt = null;
        this.state.lastAuthMealType = null;
        this.state.lastAuthTime = null;
        this.showPage('page-login');
    },

    preCheck() {
        // 사전체크 UI 제거됨 (기능 유지만)
    },

    async openQrScanner() {
        const token = localStorage.getItem('meal_token');
        if (!token) {
            showAlert("기기 인증 정보가 없습니다. 다시 로그인해주세요.", function () { app.logout(); });
            return;
        }

        this.showPage('page-scanner');

        if (!this.html5QrCode) {
            this.html5QrCode = new Html5Qrcode("reader");
        }

        const config = { fps: 10, qrbox: { width: 250, height: 250 } };

        try {
            await this.html5QrCode.start(
                { facingMode: "environment" },
                config,
                async (decodedText) => {
                    console.log("Scan success:", decodedText);
                    await this.stopScanner();
                    this.processQrAuth(decodedText);
                },
                (errorMessage) => { }
            );
        } catch (err) {
            console.error("Camera error:", err);
            showAlert("보안 정책(HTTPS 미사용)으로 인해 카메라를 시작할 수 없습니다. HTTPS 환경에서 다시 시도해 주세요.", function () { app.showPage('page-home'); });
        }
    },

    async closeScanner() {
        await this.stopScanner();
        this.showPage('page-home');
    },

    async stopScanner() {
        if (this.html5QrCode && this.html5QrCode.isScanning) {
            await this.html5QrCode.stop();
        }
    },

    async processQrAuth(qrData) {
        const token = localStorage.getItem('meal_token');
        try {
            const res = await fetch('/api/meal/qr-scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            const text = await res.text();
            let data;
            try {
                data = JSON.parse(text);
            } catch (jsonErr) {
                // 서버가 HTML을 반환한 경우 (경로 오류·ngrok·404 페이지 등)
                if (text && text.trim().toLowerCase().startsWith('<!doctype')) {
                    showAlert(
                        "서버 연동 오류: API가 HTML을 반환했습니다.\n\n" +
                        "• 접속 주소와 서버 상태를 확인해 주세요.",
                        function () { app.showPage('page-home'); }
                    );
                } else {
                    console.error("JSON parse error. Raw response:", text);
                    showAlert("서버 연동 오류: 응답 형식이 올바르지 않습니다.", function () { app.showPage('page-home'); });
                }
                this.showPage('page-home');
                return;
            }

                if (res.ok) {
                const mealType = data.meal_type || '';
                const authTime = data.auth_time || '';
                this.state.lastAuthMealType = mealType;
                this.state.lastAuthTime = authTime;
                try {
                    localStorage.setItem('meal_lastAuthMealType', mealType);
                    localStorage.setItem('meal_lastAuthTime', authTime);
                } catch (e) {}
                const mealTimeEl = document.getElementById('auth-meal-and-time');
                if (mealTimeEl) mealTimeEl.textContent = formatMealAndTime(mealType, authTime);

                const timeEl = document.getElementById('auth-time');
                if (timeEl) timeEl.textContent = data.auth_time || '';

                const empNoEl = document.getElementById('auth-emp-no');
                const userInfoEl = document.getElementById('auth-user-info');
                const user = data.user || {};
                if (empNoEl) empNoEl.textContent = user.emp_no || '';
                if (userInfoEl) userInfoEl.textContent = [user.name, user.dept_name].filter(Boolean).join(' / ') || '-';

                if (this.state.user) {
                    this.state.user = { ...this.state.user, ...user };
                    try { localStorage.setItem('meal_user', JSON.stringify(this.state.user)); } catch (e) {}
                }
                this.state.lastAuthAt = Date.now();
                try { localStorage.setItem('meal_lastAuthAt', String(this.state.lastAuthAt)); } catch (e) {}
                this.startAuth();
            } else {
                if (res.status === 401 || res.status === 403) {
                    showAlert("기기가 초기화되었거나 인증이 만료되었습니다. 다시 로그인(재인증)해 주세요.", function () { app.logout(); });
                } else {
                    showAlert(data.detail || "식수 인증에 실패했습니다.", function () { app.showPage('page-home'); });
                }
            }
        } catch (e) {
            showAlert("서버 연동 오류: " + e.message, function () { app.showPage('page-home'); });
        }
    },

    startAuth() {
        this.showPage('page-auth-success');
        this.startClock();
        // 인증 시점 기준 3분 후 만료
        const expiresAt = (this.state.lastAuthAt || Date.now()) + 3 * 60 * 1000;
        this.startCountdown(expiresAt);
    },

    startClock() {
        const dateEl = document.getElementById('auth-date');
        const clockEl = document.getElementById('auth-time');
        const update = () => {
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const dateStr = `${year}년 ${month}월 ${day}일`;

            if (dateEl) dateEl.textContent = dateStr;
            if (clockEl) clockEl.textContent = now.toTimeString().split(' ')[0];
        };
        setInterval(update, 1000);
        update();
    },

    startCountdown(expiresAtMs) {
        if (this.authCountdownTimer) {
            clearInterval(this.authCountdownTimer);
            this.authCountdownTimer = null;
        }
        const countdownEl = document.getElementById('auth-countdown');
        if (!countdownEl) return;
        const update = () => {
            const now = Date.now();
            const remainingMs = Math.max(0, expiresAtMs - now);
            const seconds = Math.ceil(remainingMs / 1000);
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            countdownEl.textContent = `남은 시간 ${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            if (remainingMs <= 0) {
                clearInterval(this.authCountdownTimer);
                this.authCountdownTimer = null;
                showAlert("인증 시간이 만료되었습니다. 다시 시도해주세요.", function () { app.goHome(); });
            }
        };
        update();
        this.authCountdownTimer = setInterval(update, 1000);
    },

    goHome() {
        this.showPage('page-home');
    },

    // 확인 후 또는 화면을 닫았다가 다시 인증 화면을 보여줄 때 사용 (오늘 인증 + 5분 이내만 표시)
    showAuthScreen() {
        if (!this.state.user) {
            showAlert("인증된 사용자 정보가 없습니다. QR 스캔을 먼저 해주세요.");
            return;
        }
        const lastAt = this.state.lastAuthAt || (localStorage.getItem('meal_lastAuthAt') && parseInt(localStorage.getItem('meal_lastAuthAt'), 10));
        const fiveMinMs = 5 * 60 * 1000;

        if (lastAt) {
            var lastDate = new Date(lastAt);
            var today = new Date();
            var isSameDay = lastDate.getFullYear() === today.getFullYear() && lastDate.getMonth() === today.getMonth() && lastDate.getDate() === today.getDate();
            if (!isSameDay) {
                showAlert("오늘 인증한 내역이 없습니다. QR 스캔을 해주세요.", function () { app.goHome(); });
                return;
            }
            if (Date.now() - lastAt > fiveMinMs) {
                showAlert("5분이 지나 인증 화면을 더 이상 표시할 수 없습니다. 담당자에게 문의 해주세요.", function () { app.goHome(); });
                return;
            }
        }

        const u = this.state.user;
        const empNoEl = document.getElementById('auth-emp-no');
        const userInfoEl = document.getElementById('auth-user-info');
        if (empNoEl) empNoEl.textContent = u.emp_no || '';
        if (userInfoEl) userInfoEl.textContent = [u.name, u.dept_name].filter(Boolean).join(' / ') || '-';
        const mealType = this.state.lastAuthMealType || localStorage.getItem('meal_lastAuthMealType') || '';
        const authTime = this.state.lastAuthTime || localStorage.getItem('meal_lastAuthTime') || '';
        const mealTimeEl = document.getElementById('auth-meal-and-time');
        if (mealTimeEl) mealTimeEl.textContent = formatMealAndTime(mealType, authTime);
        this.showPage('page-auth-success');
        this.startClock();
        // 인증화면 다시보기: 인증 시점 기준 5분 후 만료 (lastAt 없으면 현재 시점+5분)
        const expiry = lastAt ? lastAt + fiveMinMs : Date.now() + fiveMinMs;
        this.startCountdown(expiry);
    }
};

window.onload = () => app.init();

// 앱을 나갈 때 로딩으로 전환, 다시 보일 때(잠금 해제 등) init 재실행
document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
        app.showPage('page-loading');
    } else {
        app.init();
    }
});
window.addEventListener('pagehide', function () {
    app.showPage('page-loading');
});

// 뒤로가기·탭 복원 시 서버 재검증
window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
        app.init();
    }
});
