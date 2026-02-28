const app = {
    state: {
        isLoggedIn: false,
        preChecked: false,
        user: null,
        meal: null
    },

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
                        this.updateUserInfoUI();
                        this.showPage('page-home');
                        return;
                    }
                }
            } catch (e) {
                console.error("Auth status check failed:", e);
            }
            this.logout();
            return;
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
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(pageId).classList.add('active');
    },

    async loginDevice() {
        const empNo = document.getElementById('login-emp-no').value.trim();
        const name = document.getElementById('login-name').value.trim();
        const password = document.getElementById('login-password').value.trim();

        if (!empNo || !name || !password) {
            alert("사번, 이름, 초기 비밀번호를 모두 입력해주세요.");
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

                alert("기기 인증이 완료되었습니다. 이제 스캔 버튼을 눌러주세요.");
                this.showPage('page-home');
            } else {
                alert(data.detail || "인증에 실패했습니다.");
            }
        } catch (e) {
            alert("서버 연결 실패: " + e.message);
        }
    },

    logout() {
        localStorage.removeItem('meal_token');
        localStorage.removeItem('meal_user');
        this.state.isLoggedIn = false;
        this.state.user = null;
        this.showPage('page-login');
    },

    preCheck() {
        // 사전체크 UI 제거됨 (기능 유지만)
    },

    async openQrScanner() {
        const token = localStorage.getItem('meal_token');
        if (!token) {
            alert("기기 인증 정보가 없습니다. 다시 로그인해주세요.");
            this.logout();
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
            if (confirm("보안 정책(HTTPS 미사용)으로 인해 카메라를 시작할 수 없습니다. \n\n카메라 없이 시뮬레이션으로 인증을 진행하시겠습니까?")) {
                this.processQrAuth("SIMULATED_QR_DATA");
            } else {
                this.showPage('page-home');
            }
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
                    alert(
                        "서버 연동 오류: API가 HTML을 반환했습니다.\n\n" +
                        "• 접속 주소와 서버 상태를 확인해 주세요."
                    );
                } else {
                    console.error("JSON parse error. Raw response:", text);
                    alert("서버 연동 오류: 응답 형식이 올바르지 않습니다.");
                }
                this.showPage('page-home');
                return;
            }

                if (res.ok) {
                const timeEl = document.getElementById('auth-time');
                if (timeEl) timeEl.textContent = data.auth_time || '';

                const empNoEl = document.getElementById('auth-emp-no');
                const userInfoEl = document.getElementById('auth-user-info');
                const user = data.user || {};
                if (empNoEl) empNoEl.textContent = user.emp_no || '';
                if (userInfoEl) userInfoEl.textContent = [user.name, user.dept_name].filter(Boolean).join(' / ') || '-';

                this.startAuth();
            } else {
                if (res.status === 401 || res.status === 403) {
                    alert("기기가 초기화되었거나 인증이 만료되었습니다. 다시 로그인(재인증)해 주세요.");
                    this.logout();
                } else {
                    alert(data.detail || "식수 인증에 실패했습니다.");
                }
                this.showPage('page-home');
            }
        } catch (e) {
            alert("서버 연동 오류: " + e.message);
            this.showPage('page-home');
        }
    },

    startAuth() {
        this.showPage('page-auth-success');
        this.startClock();
        this.startCountdown();
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

    startCountdown() {
        let seconds = 180; // 3분
        const countdownEl = document.getElementById('auth-countdown');
        const timer = setInterval(() => {
            seconds--;
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            countdownEl.textContent = `남은 시간 ${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            if (seconds <= 0) {
                clearInterval(timer);
                alert("인증 시간이 만료되었습니다. 다시 시도해주세요.");
                this.goHome();
            }
        }, 1000);
    },

    goHome() {
        this.showPage('page-home');
    }
};

window.onload = () => app.init();

// 앱을 나갈 때 항상 로딩 화면으로 전환 → 다시 열면 복원 시 기존 화면(홈 등)이 잠깐 안 보이게
document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
        app.showPage('page-loading');
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
