# Meal Manage (식당 인증/관리 시스템)

Antigravity AI에서 Cursor로 이관한 프로젝트입니다.

## 구성

- **백엔드**: FastAPI (main.py) — API + PWA/관리자 정적 파일 서빙
- **PC 관리자 앱**: PyQt5 (pc_app.py) — 대시보드, 회사/부서/사원/식사정책/원시데이터/보고서
- **프론트**: PWA (static/) + React 관리자 (static/admin/)
- **DB**: MySQL (비동기 aiomysql)

## 사전 요구사항

- Python 3.10+
- Node.js 18+ (관리자 웹 빌드 시)
- MySQL 서버

## 설정

1. **가상환경 생성 및 패키지 설치**

   ```bash
   cd d:\meal_manage
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **환경 변수**

   `.env` 파일이 있으면 그대로 사용합니다. 없으면 `app/core/config.py`의 기본값을 사용하거나 `.env`를 만들고 다음을 설정하세요.

   ```
   DATABASE_URL=mysql+aiomysql://USER:PASSWORD@localhost:3306/meal_db
   SECRET_KEY=your-secret-key
   ```

3. **DB 준비**

   ```bash
   python repair_db.py
   ```

   (테이블 생성/컬럼 보정, 기본 admin 사용자 생성)

4. **관리자 웹(React) 빌드 (선택)**

   ```bash
   cd static\admin
   npm install
   npm run build
   cd ..\..
   ```

   이미 `static/admin/dist`가 있으면 생략 가능합니다.

## 실행

- **API 서버** (브라우저 PWA + 관리자 웹 제공)

  ```bash
  python main.py
  ```

  → http://localhost:8000 (PWA), http://localhost:8000/admin (관리자)

- **PC 관리자 앱**

  ```bash
  python pc_app.py
  ```

  (서버가 8000에서 떠 있어야 합니다.)

## URL/설정 변경

- **API 주소**: `pc_app.py` 상단 `API_BASE_URL`, `WS_URL` 수정
- **타임아웃**: `API_TIMEOUT` (초)

## 폴더 구조

```
meal_manage/
├── app/           # FastAPI 앱 (api, core, models, schemas)
├── static/       # PWA + 관리자 프론트 (admin은 React 빌드 결과 포함)
├── main.py       # 서버 진입점
├── pc_app.py     # PC 관리자 앱
├── repair_db.py  # DB 스키마/보정
├── check_db.py   # 테이블 점검
├── requirements.txt
├── .env          # (선택) 환경 변수
└── README.md
```

## Cursor에서 열기

1. **File → Open Folder** → `d:\meal_manage` 선택
2. 터미널에서 위 설정/실행 순서대로 진행

이제 이 폴더를 기준으로 개발을 이어가시면 됩니다.
