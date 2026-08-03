# ENA 가치+

ENA 콘텐츠제작센터 성과 관리 · 콘텐츠 가치 확장 분석 대시보드 (Streamlit)

## 로컬 실행

```bash
pip install -r requirements.txt
cp .env.example .env   # 값 입력
streamlit run app.py
```

브라우저: http://localhost:8501

## Streamlit Community Cloud 배포

1. 이 저장소를 GitHub에 push
2. [share.streamlit.io](https://share.streamlit.io) → **New app**
3. 설정
   - **Repository**: `BAEKILDU/ENA-` (또는 본인 fork)
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. **Advanced settings → Secrets** 에 아래 형식 등록 (`.streamlit/secrets.toml.example` 참고)

```toml
OPENAI_API_KEY = "sk-..."
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_ANON_KEY = "eyJ..."
```

5. Deploy

### Supabase 사전 준비

SQL Editor에서 순서대로 실행:

1. `sql/nielsen_channel_ratings.sql`
2. `sql/revenue_records.sql`
3. `sql/original_programs.sql`

관리자 페이지 또는 로컬 스크립트로 닐슨·매출 엑셀을 업로드하면 대시보드에 반영됩니다.

```bash
python scripts/upload_nielsen_channel_ratings.py
python scripts/extract_and_apply_original_content.py
```

## 주요 구조

| 경로 | 설명 |
|------|------|
| `app.py` | Streamlit 진입점 |
| `views/` | 화면 (홈, 예능, 신규기획, 관리자 등) |
| `data/` | 닐슨·매출·오리지널 콘텐츠 로더 |
| `data/processed/` | 오리지널 콘텐츠 분류 CSV (로컬 폴백) |
| `sql/` | Supabase 스키마 |
| `.streamlit/config.toml` | 테마·서버 설정 |

## 환경 변수

| 키 | 용도 |
|----|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_ANON_KEY` | anon public key |
| `OPENAI_API_KEY` | 기획안 분석(선택) |
| `SUPABASE_SERVICE_ROLE_KEY` | 업로드용(선택) |
