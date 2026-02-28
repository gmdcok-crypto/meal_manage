# GitHub 올리기 (Railway 배포 전)

## 1. GitHub 저장소 만들기
- https://github.com/new 접속
- Repository name: `meal_manage` (또는 원하는 이름)
- Public 선택 후 **Create repository** (README 추가 안 해도 됨)

---

## 2. 로컬에서 Git 초기화 및 커밋

```bash
cd d:\meal_manage

# 처음 한 번만
git init

# 원격 저장소 연결 (본인 계정/저장소명으로 변경)
git remote add origin https://github.com/본인아이디/meal_manage.git

# 전체 추가 (.gitignore 제외된 것만 제외됨)
git add .

# 상태 확인 ( .env, node_modules, venv 등은 안 올라가야 함)
git status

# 첫 커밋
git commit -m "Initial commit: PWA meal auth + admin"
```

---

## 3. 브랜치 이름 맞추기 (필요 시)
- 기본 브랜치가 `main` 이면:
```bash
git branch -M main
git push -u origin main
```
- `master` 쓰면:
```bash
git push -u origin master
```

---

## 4. 확인
- GitHub 저장소 페이지에서 파일 목록 확인
- **올라가면 안 되는 것**: `.env`, `venv/`, `static/admin/node_modules/`, `__pycache__/`  
  → `.gitignore` 에 있어서 제외됨

---

## 5. 관리자 화면(React) 배포 시
- `static/admin/dist/` 는 **.gitignore에 있음** → 기본적으로 안 올라감.
- **선택 1**: 로컬에서 `npm run build` 한 뒤, `.gitignore`에서 `static/admin/dist/` 한 줄 지우고, `dist` 폴더 추가 후 커밋해서 푸시.
- **선택 2**: Railway에서 빌드 단계 추가 (Nixpacks에서 admin 빌드 실행). → 별도 설정 필요.

먼저 **선택 1**로 `dist`까지 커밋해 두면 Railway에서 별도 빌드 없이 `/admin` 바로 동작함.

---

## 6. 이후 수정 시
```bash
git add .
git commit -m "메시지"
git push
```
푸시하면 Railway가 자동으로 다시 배포할 수 있음 (Railway에서 GitHub 연동한 경우).
