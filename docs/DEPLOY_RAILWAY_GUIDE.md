# 백엔드 Railway 배포 가이드 (GitHub 포함)

PWA 식당 인증 시스템(meal_manage) 백엔드를 Railway에 배포하기 위한 전체 세팅 과정을 정리한 문서입니다.

---

## 목차

1. [GitHub 저장소 세팅](#1-github-저장소-세팅)
2. [Railway 프로젝트 생성 및 GitHub 연동](#2-railway-프로젝트-생성-및-github-연동)
3. [MySQL 데이터베이스 추가](#3-mysql-데이터베이스-추가)
4. [웹 서비스 환경 변수 설정](#4-웹-서비스-환경-변수-설정)
5. [도메인(HTTPS) 생성](#5-도메인https-생성)
6. [로컬 DB 데이터 → Railway 이전](#6-로컬-db-데이터--railway-이전)
7. [PC 관리자 프로그램 연동](#7-pc-관리자-프로그램-연동)
8. [배포 후 확인 및 트러블슈팅](#8-배포-후-확인-및-트러블슈팅)

---

## 1. GitHub 저장소 세팅

### 1.1 저장소 생성

1. https://github.com/new 접속 후 로그인
2. **Repository name**: `meal_manage` (또는 원하는 이름)
3. **Public** 선택
4. **Create repository** 클릭 (README, .gitignore 추가 안 해도 됨)

### 1.2 로컬에서 Git 초기화 및 푸시

```powershell
# 프로젝트 폴더로 이동
cd d:\meal_manage

# 처음 한 번만
git init

# 원격 저장소 연결 (본인 계정/저장소명으로 변경)
git remote add origin https://github.com/본인아이디/meal_manage.git

# 브랜치를 main으로
git branch -M main

# 전체 추가
git add .

# 상태 확인 (.env, venv, node_modules 등은 제외되는지 확인)
git status

# 첫 커밋
git commit -m "Initial commit: PWA meal auth + admin"

# 푸시
git push -u origin main
```

### 1.3 이후 코드 수정 시

```powershell
cd d:\meal_manage
git add .
git commit -m "변경 내용 요약"
git push
```

- `.gitignore`에 의해 `.env`, `venv/`, `static/admin/node_modules/`, `__pycache__/` 등은 자동 제외됩니다.

---

## 2. Railway 프로젝트 생성 및 GitHub 연동

### 2.1 Railway 가입 및 로그인

- https://railway.app 접속 후 GitHub 계정으로 로그인

### 2.2 새 프로젝트 생성

1. **New Project** 클릭
2. **Deploy from GitHub repo** 선택
3. 저장소 목록에서 **meal_manage** (또는 본인 저장소명) 선택
4. 권한 요청 시 **Authorize** 승인
5. 연결되면 자동으로 빌드·배포가 시작됩니다.

### 2.3 빌드 설정 (선택)

- 프로젝트 루트의 `railway.json` / `nixpacks.toml` 이 있으면 Railway가 자동 인식합니다.
- Python + (선택) Node(React admin 빌드) 구성은 `nixpacks.toml`로 조정 가능합니다.

---

## 3. MySQL 데이터베이스 추가

### 3.1 MySQL 서비스 추가

1. Railway 프로젝트 대시보드에서 **+ New** 클릭
2. **Database** → **Add MySQL** 선택
3. MySQL 서비스가 생성되면 **Variables** 탭에서 연결 정보 확인

### 3.2 연결 정보 확인

- **Variables** 탭에서 다음 변수를 확인합니다.
  - `MYSQL_PUBLIC_URL`: 외부(로컬 PC 등)에서 접속할 때 사용
  - `MYSQL_URL` 또는 내부용 URL: Railway 앱에서 DB 접속 시 사용 가능 (동작하지 않는 환경도 있음)
- **비밀번호**: `MYSQL_ROOT_PASSWORD` 값 (복사해 두기)

### 3.3 DB 테이블 생성 (Railway DB에 스키마 넣기)

로컬 PC에서 Railway MySQL **Public URL**로 접속해 테이블을 만듭니다.

```powershell
cd d:\meal_manage

# Railway MySQL Public URL (mysql:// → mysql+aiomysql:// 로 앞만 변경)
$env:DATABASE_URL="mysql+aiomysql://root:비밀번호@호스트:포트/railway"
python repair_db.py
```

- `비밀번호`, `호스트`, `포트`는 Railway MySQL 서비스 **Variables**의 `MYSQL_PUBLIC_URL`에서 확인
- 예: `mysql://root:xxxx@ballast.proxy.rlwy.net:39282/railway`  
  → `mysql+aiomysql://root:xxxx@ballast.proxy.rlwy.net:39282/railway`

---

## 4. 웹 서비스 환경 변수 설정

배포된 **웹 서비스**(meal_manage 앱, GitHub에서 빌드된 서비스)를 클릭한 뒤 **Variables** 탭에서 설정합니다.

### 4.1 필수 변수

| 변수명 | 값 | 설명 |
|--------|-----|------|
| **DATABASE_URL** | `mysql+aiomysql://root:비밀번호@호스트:포트/railway` | Railway MySQL **Public URL**을 사용. 앞부분을 `mysql+aiomysql://` 로 맞춤. (Private URL `mysql.railway.internal` 은 이름 해석이 안 되는 환경이 있음) |
| **SECRET_KEY** | 영문·숫자 조합 긴 문자열 | JWT 등에 사용. 예: `my-super-secret-key-change-this-12345` |

### 4.2 선택 변수

| 변수명 | 값 | 설명 |
|--------|-----|------|
| **ENV** | `production` | 넣으면 개발용 reload 비활성화 |

### 4.3 DATABASE_URL 입력 예시

- MySQL 서비스 **Variables**에서 `MYSQL_PUBLIC_URL` 값 복사
- `mysql://` 를 **`mysql+aiomysql://`** 로만 바꿔서 **웹 서비스** Variables에 **DATABASE_URL** 로 추가

예시 (비밀번호는 본인 Railway MySQL 값으로):

```
mysql+aiomysql://root:saAMHleSZsjBtxPSLzleADtRJFRhSBCS@ballast.proxy.rlwy.net:39282/railway
```

- 변수 추가·수정 후 **Redeploy** 한 번 실행해야 적용됩니다.

---

## 5. 도메인(HTTPS) 생성

1. **웹 서비스** 선택
2. **Settings** 탭
3. **Networking** → **Generate Domain** 클릭
4. 발급된 주소 예: `https://web-production-e758d.up.railway.app`
5. 이 주소가 PWA·API·관리자 접속용 주소입니다.

---

## 6. 로컬 DB 데이터 → Railway 이전

로컬 MySQL(meal_db)에 이미 데이터가 있을 때, Railway DB(railway)로 복사하는 방법입니다.

### 6.1 사전 조건

- 로컬에서 Railway MySQL **Public URL**로 접속 가능해야 합니다.
- Railway DB에는 이미 `repair_db.py` 로 테이블이 생성된 상태여야 합니다.

### 6.2 이전 스크립트 실행

```powershell
cd d:\meal_manage

# Railway Public URL 설정
$env:RAILWAY_DATABASE_URL="mysql+aiomysql://root:비밀번호@호스트:포트/railway"

# 로컬 DB가 다른 주소/비밀번호면 (선택)
$env:LOCAL_DATABASE_URL="mysql+aiomysql://root:로컬비밀번호@localhost:3306/meal_db"

# 데이터 복사 실행
python migrate_to_railway.py
```

- 복사 순서: companies → departments → users → meal_policies → meal_logs → audit_logs
- 완료 후 DB 관리 툴로 Railway DB에 데이터가 들어갔는지 확인합니다.

---

## 7. PC 관리자 프로그램 연동

### 7.1 기본 동작

- PC 앱(`pc_app.py`)은 기본적으로 **Railway 배포 주소**로 API를 호출합니다.
- 설정된 기본 주소: `https://web-production-e758d.up.railway.app` (프로젝트에 따라 다를 수 있음)

### 7.2 Railway 주소 변경 시

- `pc_app.py` 상단의 `_DEFAULT_RAILWAY` 값을 실제 도메인으로 수정한 뒤 저장합니다.

### 7.3 로컬 백엔드 사용 시

- 로컬에서만 백엔드를 켜고 PC 앱을 쓰려면, 실행 전에 환경 변수로 API 주소를 지정합니다.

**PowerShell:**

```powershell
$env:MEAL_API_BASE_URL="http://localhost:8000/api/admin"
python pc_app.py
```

**CMD:**

```cmd
set MEAL_API_BASE_URL=http://localhost:8000/api/admin
python pc_app.py
```

---

## 8. 배포 후 확인 및 트러블슈팅

### 8.1 확인 사항

- **PWA**: `https://생성된도메인.up.railway.app/` → 로그인·기기 인증 화면
- **API**: `https://생성된도메인.up.railway.app/api/health` → `{"status":"ok",...}`
- **PC 앱**: 실행 후 회사/사원/원시 데이터 등이 보이는지 확인

### 8.2 PC 앱에서 데이터가 안 보일 때

1. **웹 서비스** Variables에 **DATABASE_URL**이 **Public URL**로 올바르게 들어가 있는지 확인
2. 값 앞뒤 공백·따옴표 없이 한 줄로만 입력했는지 확인
3. 수정 후 **Redeploy** 실행
4. DB 관리 툴로 Railway DB에 실제로 데이터가 있는지 확인 (없으면 [6. 로컬 DB 데이터 이전](#6-로컬-db-데이터--railway-이전) 실행)

### 8.3 배포가 CRASHED 일 때

- **Deployments** → 최신 배포 → **View Logs** 에서 에러 메시지 확인
- `DATABASE_URL` 형식 오류, `mysql.railway.internal` 이름 해석 실패 등은 **Public URL**로 바꾸면 해결되는 경우가 많습니다.

### 8.4 요약 체크리스트

- [ ] GitHub 저장소 생성 및 코드 푸시
- [ ] Railway New Project → Deploy from GitHub repo 연결
- [ ] Railway에서 MySQL 추가
- [ ] 웹 서비스 Variables에 **DATABASE_URL**(Public URL, `mysql+aiomysql://`), **SECRET_KEY** 설정
- [ ] `repair_db.py` 로 Railway DB 테이블 생성
- [ ] (선택) `migrate_to_railway.py` 로 로컬 데이터 이전
- [ ] Settings → Generate Domain 으로 HTTPS 주소 생성
- [ ] PWA·API·PC 앱으로 동작 확인

---

*문서 버전: 2026-02-28, meal_manage 프로젝트 기준*
