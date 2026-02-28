# Railway 배포 (meal_manage 백엔드)

## 1. 프로젝트 연결
- Railway 대시보드에서 **New Project** → **Deploy from GitHub repo** (또는 CLI로 연결)
- 이 저장소(`meal_manage`) 선택

## 2. 환경 변수 설정 (Variables)
Railway 프로젝트 → **Variables** 탭에서 아래 추가:

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `DATABASE_URL` | MySQL 연결 문자열 (필수) | `mysql+aiomysql://user:password@host:3306/meal_db` |
| `SECRET_KEY` | JWT 서명용 (필수, 배포 시 변경) | 영문/숫자 조합 긴 문자열 |
| `ENV` | 배포 환경 (선택) | `production` 이면 reload 끔 |

- Railway에서 **MySQL 플러그인** 쓰면 `DATABASE_URL` 자동 생성됨.
- 외부 MySQL 쓰면 해당 호스트/계정으로 연결 문자열 설정.

## 3. 빌드/실행
- **Procfile** 또는 **railway.json** 의 `startCommand` 로 `uvicorn` 실행
- Railway가 `PORT` 를 주입하므로 별도 포트 설정 불필요
- 배포 후 **Settings → Generate Domain** 으로 HTTPS 주소 발급

## 4. 참고
- **PyQt5 / PyQtWebEngine**: PC 전용 앱(`pc_app.py`)용. Railway는 웹 백엔드만 배포하므로 빌드가 무거우면 `requirements.txt`에서 제거 후 배포해도 됨 (로컬 PC 앱은 그대로 두고, Railway용은 별도 requirements 파일로 분리 가능).
