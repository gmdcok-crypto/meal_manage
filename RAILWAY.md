# Railway에서 할 일 (meal_manage 배포)

## 1. 새 프로젝트 + GitHub 연결
1. https://railway.app 로그인
2. **New Project** 클릭
3. **Deploy from GitHub repo** 선택
4. 저장소 목록에서 **gmdcok-crypto/meal_manage** 선택 (권한 요청 시 Authorize)
5. 연결되면 자동으로 빌드/배포 시도 시작

---

## 2. MySQL 추가 (DB 사용할 경우)
1. 프로젝트 대시보드에서 **+ New** 클릭
2. **Database** → **Add MySQL** 선택
3. 생성되면 MySQL 서비스가 생기고, **Variables** 탭에 `MYSQL_URL` 또는 `DATABASE_URL` 비슷한 변수가 보임
4. **meal_manage 백엔드 서비스**로 가서 **Variables**에 아래 추가:
   - Railway가 제공하는 변수 중 **MySQL 연결 URL**을 복사해서
   - 이름을 **`DATABASE_URL`** 로 하고, 값은 **`mysql+aiomysql://...`** 형태로 맞추기  
     (Railway MySQL은 보통 `mysql://...` 인데, 우리 앱은 `mysql+aiomysql://...` 필요. 예: `mysql://user:pass@host:port/railway` → `mysql+aiomysql://user:pass@host:port/railway` 로 앞만 바꿔서 넣기)

**DB 없이 일단 동작만 확인**하려면:  
- `DATABASE_URL` 없이 배포하면 앱이 뜨다가 DB 연결 시 에러 날 수 있음.  
- DB 쓰려면 위처럼 MySQL 추가 후 `DATABASE_URL` 반드시 설정.

---

## 3. 환경 변수 설정 (백엔드 서비스)
배포된 **웹 서비스**(meal_manage 코드가 배포된 서비스) 클릭 → **Variables** 탭:

| 변수명 | 값 | 필수 |
|--------|-----|------|
| **DATABASE_URL** | `mysql+aiomysql://사용자:비밀번호@호스트:3306/DB명` (Railway MySQL 추가 시 연결 정보에서 복사 후 앞에 `mysql+aiomysql` 로 맞춤) | ✅ DB 쓸 때 |
| **SECRET_KEY** | 영문/숫자 조합 긴 문자열 (예: `my-super-secret-key-change-this-12345`) | ✅ |
| **ENV** | `production` | 선택 (넣으면 reload 끔) |

**⚠️ PC 앱에서 데이터가 안 보이면:** 웹 서비스에 **DATABASE_URL**이 없어서 백엔드가 localhost DB를 보는 상태입니다.  
Railway MySQL 서비스의 **Variables**에서 연결 URL을 복사한 뒤, **웹 서비스(meal_manage)** 의 **Variables**에 **DATABASE_URL**로 추가하세요.  
- **Railway 내부용**(웹 서비스→MySQL): `mysql+aiomysql://root:비밀번호@mysql.railway.internal:3306/railway`  
- **앞부분만** `mysql://` → `mysql+aiomysql://` 로 바꾸면 됩니다.

변수 추가/수정 후 **Redeploy** 한 번 하면 적용됨.

---

## 4. 도메인(HTTPS 주소) 만들기
1. 배포된 **웹 서비스** 선택
2. **Settings** 탭
3. **Networking** → **Generate Domain** 클릭
4. 나온 주소 예: `https://meal-manage-production-xxxx.up.railway.app`
5. 이 주소가 **실제 접속 주소** (모바일에서 이 주소로 접속하면 됨)

---

## 5. 빌드 실패할 때 (PyQt 등)
- **PyQt5 / PyQtWebEngine** 때문에 Linux 빌드가 실패하면:
  - `requirements.txt` 에서 해당 두 줄 주석 처리 또는 삭제 후 커밋 → 푸시  
  - (로컬 PC 앱은 별도 가상환경에서 기존 requirements 로 유지)

---

## 6. 배포 후 확인
- 브라우저에서 **https://생성된도메인.up.railway.app** 접속
- PWA 로그인 화면이 보이면 성공
- **/admin** → 관리자 화면 (React 빌드 결과가 있으면 표시)

---

## 요약 체크리스트
- [ ] New Project → Deploy from GitHub → **gmdcok-crypto/meal_manage** 선택
- [ ] (선택) Database → Add MySQL → 연결 정보를 **DATABASE_URL** 형태로 백엔드 Variables에 설정
- [ ] Variables에 **SECRET_KEY** 추가
- [ ] Settings → **Generate Domain** 으로 HTTPS 주소 생성
- [ ] 생성된 주소로 접속해서 동작 확인
