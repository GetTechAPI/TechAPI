# TechAPI 프로젝트 명세서

> **Open data platform for consumer electronics specs**  
> Free, open, and static — no key required

| 항목 | 값 |
|---|---|
| **문서 버전** | v1.0 (Phase 0 착수 준비 완료) |
| **최종 수정** | 2026-05-26 |
| **상태** | ✅ **구현 핸드오프 준비 완료** — 모든 핵심 결정 완료 |
| **용도** | 자율 구현자(사람/도구)에게 전달되는 핸드오프 명세서 (§0.5 참조) |
| **문서 라이선스** | CC-BY 4.0 |

---

## 목차

0. 메타 정보 & 문서 사용법
0.5. **For the Implementer** ⭐
1. 개요와 비전
2. 목표 / 비목표
3. 스코프
4. 기술 아키텍처
5. 리포지토리 구조 (현재 + 목표)
6. 데이터 모델
7. API 설계
8. 점수 시스템
9. 데이터 수집 전략
10. 라이선스 정책
11. 로드맵 (Phase 0 ~ Beyond)
12. GitHub Projects 운영
13. 마이그레이션 계획 (개인 → 조직)
14. 컨벤션 (코드·네이밍·Git)
15. 테스트 전략
16. CI/CD
17. 운영·관측
18. 보안
19. 성능 목표
20. 운영 리스크 매트릭스
21. 커뮤니티·기여
22. 향후 전략
23. 의사결정 로그 (ADR)
24. 용어집
25. 참고자료

부록 A: Day 1 To-Do  
부록 B: 환경 변수 카탈로그  
부록 C: API 응답 전체 예시  
부록 D: 조직 마이그레이션 체크리스트

---

## 0. 메타 정보 & 문서 사용법

### 0.1 이 문서의 목적

이 명세서는 TechAPI 프로젝트의 **북극성(North Star)** 입니다:

- 헷갈릴 때 돌아올 곳
- 결정의 근거 보존
- 외부 기여자 온보딩 자료
- 미래의 본인을 위한 메모

### 0.2 Living Document 원칙

- 이 문서는 **고정 청사진이 아닌 진화하는 명세**
- 모든 주요 변경은 `§23 의사결정 로그`에 기록
- 분기에 한 번 전체 검토 권장
- 실제 구현과 어긋난 부분은 PR로 정정

### 0.3 표기 컨벤션

- `code`: 파일명, 명령어, 식별자
- **굵게**: 결정사항·강조
- `[ ]` / `[x]`: 미완료 / 완료
- §N.M: 다른 섹션 참조
- 🎯 향후 목표 / ✅ 합의된 결정 / ❌ 안 할 것 / 🚧 작업 중

---

## 0.5 For the Implementer

이 명세서는 **자율 구현자(사람 또는 도구)가 TechAPI를 구현할 수 있도록** 설계되었습니다. 다음 순서로 읽고 구현하세요.

### 0.5.1 읽기 순서

| 단계 | 섹션 | 목적 |
|---|---|---|
| 1 | §0.5 (이 섹션) | 구현 가이드 (지금 읽는 중) |
| 2 | §1~3 | 맥락 파악 (skim) |
| 3 | §4 | 기술 스택 확정 (정확한 버전 사용) |
| 4 | §6 | 데이터 모델 (source of truth) |
| 5 | §7 | API 설계 (정확한 엔드포인트 구현) |
| 6 | §11 Phase 0 | 현재 구현 범위 |
| 7 | §14 | 컨벤션 (모두 준수) |
| 8 | §23 | 결정 근거 (막힐 때만) |
| 9 | 부록 A, C | Day 1 To-Do, 응답 예시 |

### 0.5.2 구현 우선순위 (Phase 0)

**반드시 이 순서로:**

1. 프로젝트 스캐폴딩 (§5.3 디렉토리 구조)
2. PostgreSQL 마이그레이션 (§6 모델 기반)
3. SQLModel 모델 작성 (§6 데이터 모델)
4. FastAPI 라우터 — `brands`, `smartphones`, `socs` (§7.2)
5. 시드 데이터 입력 (`data/` 폴더, JSON 20건)
6. `scripts/seed.py` — JSON → DB
7. OpenAPI 자동 생성 (Scalar UI)
8. 테스트 작성 (§15)
9. Docker + Railway 배포 (§16)
10. Phase 0 Acceptance Criteria 검증 (§11)

### 0.5.3 절대 하지 말 것 (Don'ts)

- ❌ **§6에 없는 필드 추가하지 마세요** — 새 필드 필요하면 SPEC을 먼저 업데이트 (PR)
- ❌ **§7.2에 없는 엔드포인트 만들지 마세요** — 동일
- ❌ **시크릿·API 키 commit하지 마세요** — `.env.example`은 OK, `.env`는 X
- ❌ **TechPicks-specific 로직 넣지 마세요** — 모든 사용자에게 공평한 API (§ADR-008)
- ❌ **§14 컨벤션 어기지 마세요** — 슬러그 kebab-case, 필드 snake_case
- ❌ **임의로 라이브러리 추가하지 마세요** — §4.1 스택 우선, 추가시 ADR 신규 작성

### 0.5.4 반드시 할 것 (Do's)

- ✅ **타입 힌트 100%** — Python 코드 모든 함수에 타입 명시
- ✅ **Pydantic 입력 검증** — 모든 API 입력 자동 검증
- ✅ **테스트와 함께 작성** — 라우터 1개 만들면 테스트 1개
- ✅ **에러는 §7.5 포맷으로** — `{"error": {"code", "message", "request_id"}}`
- ✅ **컬렉션 응답은 §7.4 포맷으로** — `{count, next, previous, results}`
- ✅ **마이그레이션은 Alembic** — DB 변경은 항상 마이그레이션 파일로
- ✅ **막히면 GitHub Issue** — 결정 필요한 부분은 이슈로 명확히 질문
- ✅ **변경시 SPEC 업데이트** — 기능 추가/변경하면 이 문서도 PR

### 0.5.5 Phase 0 완료 기준 (Acceptance Criteria)

다음 **모두** 통과해야 Phase 0 완료:

- [ ] `GET /v1/health` → `200 {"status": "ok", "version": "0.1.0"}`
- [ ] `GET /v1/smartphones` → 페이지네이션 응답 (§7.4 포맷)
- [ ] `GET /v1/smartphones/{slug}` → 상세 응답 (부록 C 포맷)
- [ ] `GET /v1/socs`, `/v1/socs/{slug}` 동일
- [ ] `GET /v1/brands`, `/v1/brands/{slug}` 동일
- [ ] DB에 데이터 20건 이상 (smartphones 10+, socs 5+, brands 5+)
- [ ] OpenAPI 문서 `/docs` 또는 `/scalar` 접근 가능
- [ ] 테스트 커버리지 > 60% (`pytest --cov`)
- [ ] CI 그린 (push to main 시)
- [ ] Railway 또는 Fly.io에 배포 + HTTPS
- [ ] README에 작동하는 "Try it" 예시 (curl 한 줄)
- [ ] `docker-compose up` 한 번에 로컬 실행 가능
- [ ] `.env.example` 완비 (부록 B 참조)

### 0.5.6 막힐 때 결정 트리

```
질문: "이걸 어떻게 구현해야 하지?"
├── §6, §7에 명시되어 있나? → 그대로 구현
├── §23 ADR에 결정 근거 있나? → 따라가기
├── 컨벤션(§14)에 답 있나? → 따라가기
└── 위 모두 NO →
    ├── 유사 오픈 API는 어떻게 했나? → 참고
    ├── FastAPI 공식 권장은? → 따라가기
    └── 그래도 모르면 → GitHub Issue로 SPEC PR 요청
```

### 0.5.7 출력 형식

- **PR 제목**: Conventional Commits (§14.5) — `feat(api): add /smartphones endpoint`
- **PR 본문**: 무엇을·왜·어떻게 + 테스트 결과 스크린샷
- **커밋**: 작은 단위, 의미 있는 메시지
- **문서 업데이트**: 코드 변경 시 SPEC, README 동기화

### 0.5.8 첫 PR 권장 범위

너무 크게 잡지 말 것. 권장 첫 PR:

```
feat: project scaffolding + health endpoint

- FastAPI 초기 셋업
- /v1/health 엔드포인트
- Docker compose 로컬 환경
- 기본 테스트 1개
- README 초안
```

이게 머지된 후 → 모델 → 라우터 → 데이터 시드 → 배포 순.

---

## 1. 개요와 비전

### 1.1 한 줄 정의

> TechAPI는 다양한 앱·웹 플랫폼·AI 에이전트가 소비자 전자기기 스펙을 공통으로 활용할 수 있도록 만든 무료·공개 RESTful API. TechPicks 앱이 첫 사용자(reference consumer).

### 1.2 비전

> 개발자가 "iPhone 17 Pro의 칩 정보 가져오기" 같은 작업을 한 줄로 끝낼 수 있는 세상.
>
> 스펙 비교 앱·리뷰 사이트·가격 추적 도구·AI 에이전트·학술 연구자가 모두 같은 데이터 소스를 쓰는 세상.

### 1.3 미션

- **표준화**: 흩어진 전자기기 스펙을 일관된 구조로
- **개방**: 무료, API 키 없이 시작, 오픈소스 알고리즘
- **신뢰**: 출처 명시, 검증 가능, 버전 관리되는 데이터
- **확장 가능**: 카테고리·언어·기여자 모두 확장 가능

### 1.4 영감: 정적 오픈 데이터 API에서 가져온 5가지 패턴

1. **오픈소스 정체성** — 코드·데이터·문서·인프라 전부 공개. 누구나 self-host 가능
2. **단순한 RESTful 구조** — 슬러그 기반 URL
3. **풍부한 관계 모델링** — 포켓몬↔능력↔기술↔타입 연결
4. **다중 리포 분리** — API / 데이터 / 이미지 / SDK 각각
5. **정적 JSON 덤프** — 서버 의존 없이 사용 가능 (api-data 리포)
6. **공식 SDK 다언어 지원** — 여러 언어용 클라이언트 라이브러리 제공

TechAPI는 이 패턴을 **소비자 전자기기 도메인**에 적용.

**접근 모델**: 완전 익명이 아닌 **TMDB식 무료 등록 + 토큰 발급** 채택 (§7.6 참조). 이유는 사용 추적·악용 방지·점진적 티어링.

### 1.5 운영 주체

| 항목 | 현재 | 목표 |
|---|---|---|
| **GitHub 리포** | `[메인테이너]/TechAPI` (개인 계정) | `GetTechAPI/techapi` |
| **GitHub 조직** | `GetTechAPI` 예약만 (비어있음) | 5+ 리포 보유 |
| **공식 도메인** | (없음) | `techapi.dev` |
| **첫 사용자 (Reference Consumer)** | TechPicks 앱 (별도 프로젝트) | TechPicks + 가격비교 사이트 + AI 에이전트 + 연구자 등 다중 사용자 |
| **연락처** | GitHub Issues | `team@techapi.dev` |

### 1.6 핵심 가치

- **오픈소스 우선** — 코드(MIT)·데이터(CC-BY-SA)·문서·인프라 코드 전부 공개. Self-host 가능.
- **플랫폼 사고** — TechAPI는 특정 앱의 백엔드가 아닌 다수 사용자가 공유하는 공공 인프라. TechPicks는 첫 사용자일 뿐, 마지막 사용자가 아님.
- **개발자 우선** — 소비자 UI는 TechPicks 같은 별도 프로젝트 책임. TechAPI는 API 안정성·문서 품질에 집중.
- **데이터 정확성** — 출처 명시 없는 데이터는 들이지 않음
- **장기 유지** — 빠른 출시보다 지속 가능한 운영
- **투명성** — 알고리즘·데이터 소스·결정 근거 모두 공개. 토큰 시스템 운영 통계도 공개

---

## 2. 목표 / 비목표

### 2.1 v1 Goals (Phase 0~3까지 달성)

- ✅ 누구나 무료로 사용 가능한 공개 REST API
- ✅ **다중 사용자 플랫폼** — TechPicks 외에도 다른 앱·웹·AI 에이전트가 동일하게 사용
- ✅ 스마트폰·SoC·GPU의 정확하고 구조화된 스펙
- ✅ 자체 점수 시스템 (오픈소스 알고리즘)
- ✅ 카테고리 간 관계 (스마트폰 ↔ SoC, SoC ↔ GPU)
- ✅ 라이브 API + 정적 JSON 덤프 둘 다 제공
- ✅ 영문 우선, 한국어 필드 부가 제공
- ✅ OpenAPI 자동 문서
- ✅ 안정적 버저닝 (외부 사용자의 의존성 보호)

### 2.2 장기 Goals (Phase 4+)

- 🎯 GraphQL 지원
- 🎯 다국어 필드 (en, ko, ja, zh)
- 🎯 데이터 시계열 (가격 변동, 펌웨어 업데이트 추적)
- 🎯 자체 측정 벤치마크 (가능한 카테고리만)
- 🎯 100+ 외부 기여자 커뮤니티
- 🎯 다언어 공식 SDK (JS/TS, Python, Swift, Kotlin)
- 🎯 TechPicks 외 외부 사용 사례 5+

### 2.3 Non-goals (명시적으로 안 함)

- ❌ **TechPicks 전용 기능** → API는 모든 사용자에게 공평. TechPicks-specific 로직은 TechPicks 내부에서 처리
- ❌ 가격 비교·전자상거래 → 앱 단의 책임
- ❌ 사용자 리뷰·평점 → TechAPI는 객관 데이터만
- ❌ 개인화·추천 → 앱 단
- ❌ 폐쇄형 벤치마크 점수 **재배포** → Geekbench·AnTuTu 등은 알고리즘 입력으로만 사용
- ❌ 자체 호스팅 이미지 → 제조사 자산 무단 재호스팅 안 함
- ❌ 실시간 가격 API → 별도 이커머스 API 필요한 영역
- ❌ 사용자 인증 (Phase 4 API 키 외)

---

## 3. 스코프

### 3.1 v1 포함 카테고리

| 카테고리 | 목표 데이터 수 | 우선순위 |
|---|---|---|
| **Smartphones** | ~500 (2020년 이후 주요 모델) | P0 |
| **SoCs** | ~200 (Snapdragon, MediaTek, Apple, Exynos, Tensor) | P0 |
| **Discrete GPUs** | ~150 (NVIDIA RTX, AMD Radeon, Intel Arc) | P1 |
| **Brands** | ~50 (제조사·SoC 메이커) | P0 |

### 3.2 v2+ 확장 (시간순)

1. 태블릿
2. 노트북·랩탑 (CPU 포함)
3. 데스크탑 CPU
4. 디스플레이 모듈 (패널 제조사·스펙)
5. 카메라 센서 (Sony IMX 등)
6. 무선 이어폰 / 헤드폰
7. 스마트워치 / 웨어러블
8. 게이밍 콘솔
9. SBC (라즈베리파이 등)

### 3.3 절대 안 다룰 영역

- 자동차 (도메인이 너무 다름)
- 백색가전 (냉장고·세탁기)
- 산업용 장비
- 의료 기기

---

## 4. 기술 아키텍처

### 4.1 스택 결정

| 영역 | 선택 | 대안 | 선택 이유 |
|---|---|---|---|
| 백엔드 | **FastAPI** (Python 3.12) | NestJS, Spring Boot | 빠른 개발, 자동 OpenAPI, async, 학습 곡선 낮음 |
| DB | **PostgreSQL 16** (Supabase) | MySQL, MongoDB | 관계형 + JSONB, 운영 부담 적음 |
| ORM | **SQLModel** | SQLAlchemy raw, Prisma | FastAPI 친화적, Pydantic 통합 |
| 캐시 | Redis (Phase 2+) | Memcached, in-memory | 표준, 다용도 |
| 배포 | **Railway** 또는 Fly.io | AWS ECS, Render | 솔로 친화, 무료 티어 |
| 문서 | **Scalar** | Swagger UI, Redoc | 모던 UI, OpenAPI 호환 |
| 정적 데이터 | GitHub raw URLs | S3, R2 | 무료, 버전 관리, CDN |
| 이미지 | GitHub + jsDelivr | S3, R2, Cloudinary | 무료, CDN 자동 |

### 4.2 데이터 흐름

```
┌─────────────────────────┐
│   데이터 입력           │
│   (수동/스크래핑/PR)     │
└──────────┬──────────────┘
           ▼
    ┌──────────────┐
    │ PostgreSQL   │ (Supabase 호스팅)
    │ + JSONB      │
    └──────┬───────┘
           │
   ┌───────┴────────┐
   ▼                ▼
┌────────┐    ┌──────────────┐
│  API   │    │ 정적 JSON    │
│ 서버   │    │ 덤프         │
│(FastAPI)│   │(api-data 리포)│
└───┬────┘    └──────┬───────┘
    │                │
    └────────┬───────┘
             ▼
    ┌────────────────────┐
    │ 사용자             │
    │ - TechPicks 앱     │
    │ - 외부 개발자       │
    │ - 정적 사이트       │
    └────────────────────┘
```

### 4.3 시스템 컴포넌트

| 컴포넌트 | 책임 |
|---|---|
| **FastAPI 서버** | HTTP 요청 처리, 라우팅, 직렬화 |
| **SQLModel 레이어** | DB 접근, 트랜잭션 |
| **Scoring Service** | 점수 계산 (§8) |
| **Search Service** | 통합 검색 (Postgres FTS 또는 Meilisearch) |
| **Validation Service** | 입력 데이터 스키마 검증 |
| **Static Dump Generator** | DB → JSON 덤프 (GitHub Actions) |

### 4.4 인프라 의존성

| 서비스 | 목적 | 비용 |
|---|---|---|
| Supabase | PostgreSQL 호스팅 | 무료 → Pro $25/월 |
| Railway/Fly.io | API 서버 | 무료 → ~$5/월 |
| GitHub | 코드·데이터·이미지 | 무료 (공개 리포) |
| jsDelivr | 이미지 CDN | 무료 (공개 리포 자동) |
| Cloudflare | 도메인 · DNS (선택) | 무료 (DNS) + 도메인 $12/년 |

**Phase 0 총 비용**: $0/월 (도메인만 연 $12)  
**Phase 3 예상 비용**: $30~50/월

---

## 5. 리포지토리 구조

### 5.1 현재 상태 (Phase 0~1)

```
github.com/[메인테이너]/TechAPI    ← 개인 계정, 단일 리포
└── (모든 코드·데이터·문서가 여기)
```

**이유**: Codespaces 셋업·로컬 개발 환경이 이미 개인 리포에 구축되어 있어 마이그레이션 비용 회피.

### 5.2 목표 상태 (Phase 2+)

```
github.com/GetTechAPI/
├── .github          # 조직 프로필 README, 공통 워크플로
├── techapi          # 메인 API 서버 (Phase 0~1 마이그레이션)
├── api-data         # 정적 JSON 덤프 (Phase 1~2 분리)
├── images           # 제품 이미지 (Phase 2 분리)
├── techapi.dev      # 도큐먼트 사이트 (Phase 3)
├── techapi-js       # JS/TS SDK (Phase 4)
└── techapi-py       # Python SDK (Phase 4)
```

마이그레이션 트리거와 절차는 §13 참조.

### 5.3 메인 리포 내부 구조

```
techapi/
├── README.md
├── LICENSE                    # MIT
├── pyproject.toml
├── .env.example
├── .gitignore
├── .devcontainer/             # Codespaces 설정
│   └── devcontainer.json
├── .github/
│   ├── workflows/             # GitHub Actions
│   ├── ISSUE_TEMPLATE/        # 이슈 템플릿 (§12.6)
│   ├── pull_request_template.md
│   └── CODEOWNERS
├── app/
│   ├── main.py                # FastAPI 엔트리
│   ├── config.py              # 설정 (env 로드)
│   ├── database.py            # DB 연결
│   ├── dependencies.py        # FastAPI 의존성
│   ├── models/                # SQLModel
│   │   ├── brand.py
│   │   ├── smartphone.py
│   │   ├── soc.py
│   │   └── gpu.py
│   ├── routers/               # API 라우트
│   │   ├── smartphones.py
│   │   ├── socs.py
│   │   ├── gpus.py
│   │   ├── brands.py
│   │   ├── compare.py
│   │   └── search.py
│   ├── services/              # 비즈니스 로직
│   │   ├── scoring.py
│   │   ├── search.py
│   │   └── validator.py
│   └── schemas/               # Pydantic 응답 스키마
├── data/                      # 큐레이션 시드 JSON (단수 폴더명 + 브랜드 하위폴더)
│   ├── brand/                 # brand/<slug>.json (브랜드는 최상위, 하위폴더 없음)
│   ├── smartphone/<brand>/    # smartphone/samsung/galaxy-s25.json
│   ├── soc/<manufacturer>/    # soc/qualcomm/snapdragon-8-elite.json
│   ├── gpu/<manufacturer>/    # gpu/nvidia/geforce-rtx-5090.json
│   └── cpu/<manufacturer>/<year>/  # cpu/intel/2023/core-i9-14900k.json (CPU는 연도까지 분할)
│   # data/는 큐레이션(검증)된 부분집합. 자동 수집은 이 레포 밖 내부 파이프라인에서 처리
├── scripts/
│   ├── seed.py                # DB 시드 주입 (data/ 재귀 로드)
│   ├── validate.py            # 스키마 검증
│   └── dump.py                # DB → 정적 JSON 덤프
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
│   ├── SPEC.md                # 이 명세서
│   ├── API.md
│   ├── SCHEMA.md
│   ├── CONTRIBUTING.md
│   ├── CODE_OF_CONDUCT.md
│   └── decisions/             # ADR 파일들 (§23)
├── docker-compose.yml
└── Dockerfile
```

---

## 6. 데이터 모델

### 6.1 엔티티 관계도 (ERD)

```
┌──────────┐    ┌──────────┐
│  Brand   │◄───┤   SoC    │
└─────┬────┘    └─────┬────┘
      │ 1:N           │ 1:N
      │               │
      ▼               ▼
┌────────────────────────┐
│      Smartphone        │
└────────────────────────┘

┌──────────┐    ┌──────────────┐
│  Brand   │◄───┤ DiscreteGPU  │
└──────────┘    └──────────────┘
```

### 6.2 Brand
```python
class Brand:
    id: int
    slug: str                   # "samsung"
    name: str                   # "Samsung"
    country: str                # ISO 3166: "KR"
    founded_year: int | None
    logo_url: str | None
    website: str | None
    description_en: str | None
    description_ko: str | None
```

### 6.3 SoC
```python
class SoC:
    id: int
    slug: str                   # "snapdragon-8-elite"
    name: str                   # "Snapdragon 8 Elite"
    manufacturer_id: int        # FK → Brand
    release_date: date
    process_nm: float           # 3.0
    transistors_billion: float | None

    # CPU
    cpu_config: dict            # JSONB: {"performance": 2, "efficiency": 6, "clocks": [...]}

    # GPU (integrated)
    gpu_name: str               # "Adreno 830"
    gpu_cores: int | None
    gpu_clock_mhz: int | None

    # AI
    npu_tops: float | None

    # Modem
    modem: str | None

    # Benchmarks (raw, alg input only)
    geekbench_single: int | None
    geekbench_multi: int | None
    antutu_score: int | None

    # Meta
    verified: bool = False
    source_urls: list[str]
    created_at: datetime
    updated_at: datetime
```

### 6.4 Smartphone
```python
class Smartphone:
    id: int
    slug: str                   # "galaxy-s25"
    name: str                   # "Galaxy S25"
    brand_id: int               # FK → Brand
    soc_id: int                 # FK → SoC

    release_date: date
    msrp_usd: int | None

    # Memory
    ram_gb: int
    storage_options_gb: list[int]

    # Display (JSONB)
    display: dict
    # {size_inch, resolution, refresh_hz, type, brightness_nits, ppi}

    # Cameras (JSONB array)
    cameras: list[dict]
    # [{type: "main"|"ultrawide"|"telephoto"|"selfie", mp, aperture, ois, sensor}]

    # Battery
    battery_mah: int
    charging_wired_w: int | None
    charging_wireless_w: int | None

    # Physical
    weight_g: float
    dimensions: dict            # {height_mm, width_mm, depth_mm}
    ip_rating: str | None       # "IP68"

    # Software
    os: str                     # "Android" | "iOS"
    os_version: str | None

    # Connectivity
    connectivity: dict          # {wifi, bluetooth, nfc, usb}

    # Assets
    image_url: str | None
    images: list[str] = []

    # Meta
    verified: bool = False
    source_urls: list[str]
    created_at: datetime
    updated_at: datetime
```

### 6.5 Discrete GPU
```python
class DiscreteGPU:
    id: int
    slug: str                   # "rtx-5090"
    name: str                   # "GeForce RTX 5090"
    manufacturer_id: int        # FK → Brand
    architecture: str           # "Blackwell"
    release_date: date
    msrp_usd: int | None

    # Cores
    cuda_cores: int | None      # NVIDIA
    stream_processors: int | None  # AMD
    rt_cores: int | None
    tensor_cores: int | None

    # Memory
    memory_gb: int
    memory_type: str            # "GDDR7"
    memory_bus_bit: int
    memory_bandwidth_gbps: float | None

    # Clock
    base_clock_mhz: int
    boost_clock_mhz: int

    # Power
    tdp_w: int
    pcie_version: str

    # Benchmarks (open licenses only)
    blender_score: float | None
    timespy_score: int | None   # 자체 측정시만

    # Meta
    verified: bool = False
    source_urls: list[str]
```

### 6.6 부가 테이블

| 테이블 | 용도 |
|---|---|
| `categories` | 카테고리 메타 (smartphone, soc, gpu...) |
| `benchmarks` | 벤치마크 정의 (이름, max_score, 라이선스, source) |
| `benchmark_results` | 벤치마크 결과 (entity_id, benchmark_id, score, source_url) |
| `score_versions` | 점수 알고리즘 버전 트래킹 |
| `audit_log` | 데이터 변경 이력 |

### 6.7 CPU (데스크탑/랩탑 프로세서)

> 추가 결정: ADR-011 참조. v1 원안에는 없었으나 메인테이너 요청으로 추가. 모바일 `SoC`와 구분되는 별도 엔티티. 인텔 Core / AMD Ryzen 등.

```python
class CPU:
    id: int
    slug: str                   # "core-i9-14900k"
    name: str                   # "Core i9-14900K"
    manufacturer_id: int        # FK → Brand (intel, amd)
    release_date: date
    segment: str                # "desktop" | "laptop" | "hedt" | "server"
    architecture: str           # "Raptor Lake", "Zen 4"
    socket: str | None          # "LGA1700", "AM5"
    process_node: str | None    # "Intel 7", "TSMC N4" (CPU 공정명은 단일 nm float로 환원 어려움)

    cores: int
    threads: int
    p_cores: int | None
    e_cores: int | None

    base_clock_ghz: float | None
    boost_clock_ghz: float | None
    l3_cache_mb: float | None
    tdp_w: int | None           # base power (PBP/TDP)
    max_tdp_w: int | None       # turbo power (MTP/PPT)

    integrated_graphics: str | None
    memory_support: str | None  # "DDR5-5600"

    # Benchmarks (raw, alg input only — ADR-006)
    cinebench_r23_single: int | None
    cinebench_r23_multi: int | None
    geekbench_single: int | None
    geekbench_multi: int | None

    msrp_usd: int | None
    verified: bool = False
    source_urls: list[str]
    created_at: datetime
    updated_at: datetime
```

---

## 7. API 설계

### 7.1 베이스 URL

| 환경 | URL |
|---|---|
| 프로덕션 | `https://api.techapi.dev/v1/` (목표) |
| 스테이징 | `https://staging.api.techapi.dev/v1/` |
| 로컬 | `http://localhost:8000/v1/` |
| 정적 덤프 | `https://raw.githubusercontent.com/GetTechAPI/api-data/main/` |

### 7.2 엔드포인트 전체

#### 리소스
| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/smartphones` | 리스트 (페이지네이션) |
| GET | `/smartphones/{slug}` | 상세 |
| GET | `/smartphones/{slug}/score` | 점수만 |
| GET | `/socs` | 리스트 |
| GET | `/socs/{slug}` | 상세 |
| GET | `/socs/{slug}/smartphones` | 이 SoC를 쓰는 폰 |
| GET | `/gpus` | 리스트 |
| GET | `/gpus/{slug}` | 상세 |
| GET | `/cpus` | 리스트 (`?segment=desktop\|laptop`) |
| GET | `/cpus/{slug}` | 상세 |
| GET | `/brands` | 리스트 |
| GET | `/brands/{slug}` | 상세 |
| GET | `/brands/{slug}/smartphones` | 이 브랜드의 폰 |

#### 운영
| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/compare?items=a,b,c` | 비교 |
| GET | `/search?q=...` | 통합 검색 |
| GET | `/categories` | 카테고리 목록 |
| GET | `/health` | 헬스체크 |
| GET | `/version` | API 버전, 점수 알고리즘 버전 |

### 7.3 쿼리 파라미터 컨벤션

```
?limit=20              # 페이지 크기 (기본 20, 최대 100)
?offset=40             # 오프셋
?cursor=...            # 커서 페이지네이션 (큰 컬렉션)
?sort=-release_date    # 정렬 ('-' 접두사 = 내림차순)
?brand=samsung         # 필터
?soc=snapdragon-8-elite # 필터
?include=soc,brand     # 관련 리소스 임베드
?fields=id,name,slug   # 응답 필드 선택 (sparse fieldset)
?lang=ko               # 다국어 필드 (en 기본)
```

### 7.4 응답 포맷 (성공)

**리스트:**
```json
{
  "count": 487,
  "next": "/v1/smartphones?offset=20",
  "previous": null,
  "results": [
    { "slug": "galaxy-s25", "name": "Galaxy S25", "url": "/v1/smartphones/galaxy-s25" }
  ]
}
```

**상세**: 부록 C 참조.

### 7.5 에러 응답
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Smartphone with slug 'foo' not found",
    "request_id": "req_abc123",
    "documentation_url": "https://techapi.dev/docs/errors#not-found"
  }
}
```

| HTTP | code | 의미 |
|---|---|---|
| 400 | `INVALID_REQUEST` | 잘못된 쿼리 |
| 401 | `UNAUTHORIZED` | API 키 누락 (Phase 4+) |
| 403 | `FORBIDDEN` | API 키 권한 부족 |
| 404 | `NOT_FOUND` | 리소스 없음 |
| 422 | `VALIDATION_ERROR` | 파라미터 검증 실패 |
| 429 | `RATE_LIMIT_EXCEEDED` | 레이트 리밋 초과 |
| 500 | `INTERNAL_ERROR` | 서버 오류 |
| 503 | `SERVICE_UNAVAILABLE` | 일시적 장애 |

### 7.6 인증 & 레이트 리밋 (TMDB 모델)

TechAPI는 **오픈소스 + 무료 등록 필수** 모델 채택 (TMDB 방식). 완전 익명 접근은 비채택.

**왜 TMDB식인가:**
- 사용 추적 (누가 뭘 쓰는지 파악 → 데이터 우선순위 결정)
- 악용 방지 (남용 시 토큰만 차단)
- 점진적 티어링 가능 (Free → Hobby → Commercial)
- 사용자와 직접 관계 구축
- **코드는 100% 오픈소스 → 부담스러우면 self-host 가능**

#### 토큰 발급 절차

```
1. techapi.dev/signup
   ↓ (이메일 또는 GitHub OAuth)
2. 대시보드에서 토큰 발급
   ↓
3. 모든 요청에 인증 헤더
   Authorization: Bearer tk_live_abc123...
   또는
   ?api_key=tk_live_abc123...
```

#### 티어 구조

| 티어 | 요금 | 분당 | 일일 | 용도 |
|---|---|---|---|---|
| **Free** | 무료 | 60 req/min | 10,000 req/day | 개인·학습·취미 |
| **Hobby** | 무료* | 120 req/min | 50,000 req/day | 사이드 프로젝트·작은 앱 |
| **Open Source** | 무료** | 600 req/min | 무제한 | 검증된 OSS 프로젝트 |
| **Commercial** | $19/월 (Phase 5+) | 1,000 req/min | 무제한 | 상업 앱·서비스 |
| **Self-host** | 무료 | 본인 인프라 | 본인 한도 | 자체 호스팅 |

\* **Hobby**: PR 1개 머지 또는 데이터 5건 기여 시 자동 승급  
\** **Open Source**: 공개 리포 + 적극적 유지보수 확인 후 수동 승급

#### Phase별 도입 일정

| Phase | 인증 정책 |
|---|---|
| 0 (MVP) | 인증 없음 (본인만 테스트) |
| **1** | **토큰 발급 시스템 도입** ⭐ Free 티어만 |
| 2 | Hobby 티어 추가, 자동 승급 로직 |
| 3 | 대시보드 + 통계 |
| 4 | Open Source 티어 |
| 5+ | Commercial 티어 (지속 가능 운영 자금 확보 시) |

#### 응답 헤더

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 47
X-RateLimit-Reset: 1716800000
X-Daily-Quota-Limit: 10000
X-Daily-Quota-Remaining: 9523
X-Tier: free
```

#### 토큰 보안

- 발급 시 **1회만 전체 표시**, 이후 prefix만 (`tk_live_abc...`)
- 회전 지원 (옛 토큰 24시간 grace period)
- 토큰별 사용량·로그 대시보드 (Phase 3+)
- IP allowlist 옵션 (Commercial 이상, Phase 5+)
- 의심 활동 감지 시 자동 일시 정지

#### 토큰 형식

```
tk_live_{32자 랜덤}    # 프로덕션
tk_test_{32자 랜덤}    # 테스트 (Phase 4+, 더 낮은 한도)
```

#### Self-hosting 경로 (오픈소스 보장)

토큰 시스템 자체가 부담스러운 사용자를 위해:
- 코드 전체 MIT 라이선스 → 자체 인스턴스 배포 가능
- 정적 JSON 덤프 제공 → 토큰 없이 데이터만 받기 가능
- Docker 이미지 + 배포 가이드 (`docs/SELF_HOSTING.md`)
- 자체 인스턴스에서는 인증 끄거나 자체 토큰 시스템 운영 가능

**이게 오픈소스 정신과 TMDB식 운영 책임의 균형점.**

### 7.7 버저닝 정책

- **URL 버저닝**: `/v1/`, `/v2/`
- v1 → v2 전환 시 v1은 **최소 12개월 병행 운영**
- Breaking change 정의:
  - 필드 제거·이름 변경·타입 변경
  - 엔드포인트 제거
  - 응답 구조 재편
- Non-breaking (마이너 업데이트):
  - 새 필드 추가 (nullable)
  - 새 엔드포인트
  - 새 쿼리 파라미터
- 변경 발표: `/version` 엔드포인트 + GitHub release notes + 문서 업데이트

---

## 8. 점수 시스템

### 8.1 카테고리

| 점수 | 입력 데이터 |
|---|---|
| **Performance** | CPU·GPU·RAM 벤치마크 |
| **Camera** | 메인·울트라와이드·텔레포토 스펙 + DXO 등 |
| **Battery** | 용량 + 충전 속도 + 효율 (SoC nm) |
| **Display** | 해상도 + 주사율 + 밝기 + 패널 타입 |
| **Value** | 종합 점수 / MSRP |

### 8.2 계산 원칙

- 모든 점수는 **0~100 스케일**
- 알고리즘은 **오픈소스** (`app/services/scoring.py`)
- 가중치는 외부화 (`config/scoring.yaml`)
- 점수에 `algorithm_version` 부착 → 변경 추적 가능
- 입력 데이터 누락 시 **null** 반환 (0이 아님)

### 8.3 알고리즘 예시 (Performance)
```python
performance = (
    geekbench_single_normalized * 0.25 +
    geekbench_multi_normalized  * 0.30 +
    gpu_score_normalized        * 0.30 +
    ram_factor                  * 0.15
)
```

### 8.4 정규화 방식

- **Min-Max**: 각 카테고리 내 최고/최저로 0~100
- 매년 재정규화 (새 모델 출시로 천장 변동)
- 옛 데이터의 점수도 재계산되어 일관성 유지

### 8.5 비공개 데이터 처리

| 소스 | 라이선스 | 처리 |
|---|---|---|
| Geekbench Browser | 비공개 | 수치만 보존, 알고리즘 입력으로 사용, 재배포 안 함 |
| AnTuTu | 비공개 | 동일 |
| 3DMark | 비공개 | 동일 |
| Blender Open Data | CC-BY-SA | 자유 사용·재배포 가능 |
| Phoronix Test Suite | 오픈소스 | 자유 사용 |
| 자체 측정 | TechAPI 소유 | `verified_by_techapi: true` 표시 |

### 8.6 알고리즘 버저닝

```
algorithm_version: "1.2.0"
- 1.0.0: 초기 출시 (Phase 1)
- 1.1.0: Display 점수 추가 (Phase 2)
- 1.2.0: 가중치 재조정 (Phase 3)
```

옛 점수는 archive로 보관 가능.

---

## 9. 데이터 수집 전략

### 9.1 Phase별 접근

| Phase | 방식 | 목표 수 |
|---|---|---|
| 0 | 수동 JSON 입력 | 20~50 |
| 1 | 수동 + Directus/NocoDB 어드민 UI | 50~500 |
| 2 | 스크래핑 파이프라인 + 사람 검토 | 500~2000 |
| 3 | 자동화 + 기여자 PR | 2000+ |

### 9.2 데이터 소스 카탈로그

| 소스 | 라이선스 | 신뢰도 | 사용 가능 여부 |
|---|---|---|---|
| **제조사 공식 스펙시트** | 사실 데이터 | ⭐⭐⭐⭐⭐ | ✅ |
| **Wikipedia** | CC-BY-SA | ⭐⭐⭐⭐ | ✅ (출처 표기) |
| **Wikidata** | CC0 | ⭐⭐⭐⭐ | ✅ |
| **GSMArena** | ToS 제한 | ⭐⭐⭐⭐⭐ | ⚠️ 참조용, 직접 크롤 금지 |
| **NanoReview** | 비공개 | ⭐⭐⭐⭐ | ⚠️ 비교만, 데이터 추출 금지 |
| **DeviceSpecifications** | ToS 제한 | ⭐⭐⭐⭐ | ⚠️ 참조용 |
| **TechPowerUp (GPU)** | 비공개 | ⭐⭐⭐⭐⭐ | ⚠️ 참조용 |
| **Blender Open Data** | CC-BY-SA | ⭐⭐⭐⭐ | ✅ |
| **사용자 제출 PR** | 기여자 라이선스 | 가변 | ✅ (검증 필수) |

### 9.3 검증 절차

```
1. 데이터 입력/제출
   ↓
2. scripts/validate.py 자동 검증
   - 스키마 일치
   - 필수 필드
   - 단위·범위 체크 (RAM 0~64GB, 무게 0~500g 등)
   ↓
3. 사람 리뷰 (PR 또는 어드민)
   - 출처 URL 최소 1개
   - 크로스 체크 (다른 소스와 비교)
   ↓
4. 머지 → verified: true
   ↓
5. 자동 덤프 생성 → api-data 리포
```

### 9.4 기여자 데이터 받기 (Phase 1+)

- `data_addition` 이슈 템플릿으로 요청 받기
- PR로 JSON 직접 제출 가능
- 검증 자동화 → 사람 리뷰
- 머지 시 `CONTRIBUTORS.md`에 기록

---

## 10. 라이선스 정책

| 자산 | 라이선스 | 이유 |
|---|---|---|
| 코드 (techapi, SDK) | **MIT** | 가장 관대, 상업 사용 허용 |
| 데이터 (api-data) | **CC-BY-SA 4.0** | OpenStreetMap·MusicBrainz 모델, 데이터 생태계 보호 |
| 이미지 (images) | 원본 유지 | 제조사 자산, fair use 범위 |
| 문서 (docs) | **CC-BY 4.0** | 출처만 표기하면 자유 |
| 점수 알고리즘 | MIT (코드의 일부) | 검증 가능성을 위한 공개 |

### 10.1 데이터 라이선스 (CC-BY-SA) 의미

사용자는:
- ✅ 자유 사용·복제·배포·수정
- ✅ 상업 이용
- ⚠️ **저작자 표기** 필요 ("Data from TechAPI")
- ⚠️ **동일 조건 변경 허락** (파생물도 CC-BY-SA)

이게 데이터 생태계 보호 모델. OpenStreetMap이 동일.

---

## 11. 로드맵

### Phase 0 — MVP (1~2주) 🚧

- [x] GetTechAPI 조직 생성 (현재 비어있음, 예약 namespace)
- [x] 개인 계정에 TechAPI 리포 생성
- [x] Codespaces 셋업
- [ ] GitHub Project 보드 셋업 (리포 단위, `TechAPI Roadmap`)
- [ ] 명세서 (이 문서) 커밋
- [ ] FastAPI 초기 셋업
- [ ] Supabase Postgres 연결
- [ ] 4개 테이블 마이그레이션 (brands, smartphones, socs, gpus)
- [ ] 수동 시드 데이터 20건
- [ ] `/v1/smartphones`, `/v1/socs` 엔드포인트
- [ ] Scalar 자동 문서
- [ ] Railway 또는 Fly.io 배포
- [ ] **마일스톤: v0.1.0 - MVP**

### Phase 1 — 데이터 확장 + 토큰 시스템 (2~3주)

- [ ] 데이터 100건 돌파
- [ ] 점수 시스템 v1
- [ ] `/v1/compare`, `/v1/search` 엔드포인트
- [ ] **토큰 발급 시스템** ⭐ — 가입·로그인·토큰 생성
- [ ] **레이트 리밋 미들웨어** — Free 티어 (60/min, 10K/day)
- [ ] CONTRIBUTING.md, CODE_OF_CONDUCT.md
- [ ] Self-hosting 가이드 (`docs/SELF_HOSTING.md`)
- [ ] 첫 외부 기여자 모집
- [ ] **마일스톤: v0.2.0 - Data Expansion + Auth**

**Phase 1 Acceptance Criteria:**
- [ ] DB 데이터 ≥ 100건 (smartphones 50+, socs 30+, gpus 20+)
- [ ] `/v1/compare?items=a,b,c` 정상 동작 + 점수 차이 표시
- [ ] `/v1/search?q=...` 검색 정확도 80%+ (수동 평가 10건)
- [ ] 가입 → 토큰 발급 → API 호출 end-to-end 동작
- [ ] 레이트 리밋 초과 시 `429` + 정확한 헤더 반환
- [ ] 점수 알고리즘 문서화 (`app/services/scoring.py` 주석 + `docs/SCORING.md`)
- [ ] Self-host 가이드로 다른 사람이 30분 안에 로컬 실행 가능
- [ ] 테스트 커버리지 > 75%

### Phase 2 — 자동화 + 분리 (1~2개월)

- [ ] **조직 마이그레이션 트리거**: 두 번째 리포 필요 시점
- [ ] `api-data` 리포 분리 → 조직으로 이동
- [ ] `images` 리포 분리 → 조직으로 이동
- [ ] 메인 리포 `techapi` 조직으로 이전 (§13 마이그레이션)
- [ ] 스크래핑 파이프라인 구축
- [ ] GitHub Actions로 정적 덤프 자동 빌드
- [ ] 데이터 500건 돌파
- [ ] **마일스톤: v0.3.0 - Automation**

### Phase 3 — 문서화·브랜딩 (1개월)

- [ ] `techapi.dev` 도메인 확보
- [ ] 도큐먼트 사이트 (`techapi.dev` 리포)
- [ ] 조직 verified 배지
- [ ] API 키 시스템 (선택)
- [ ] 레이트 리밋 적용
- [ ] **마일스톤: v0.4.0 - Docs & Branding**

### Phase 4 — SDK·생태계 (3개월~)

- [ ] `techapi-js` SDK
- [ ] `techapi-py` SDK
- [ ] TechPicks 앱에서 자체 API → TechAPI로 마이그레이션
- [ ] GitHub stars 100+
- [ ] **마일스톤: v1.0.0 - Public Launch**

### Phase 5+ — 장기 (1년 이후)

- [ ] GraphQL 엔드포인트
- [ ] 다국어 필드 (ko, ja, zh)
- [ ] 시계열 데이터 (가격, 펌웨어)
- [ ] 자체 측정 벤치마크
- [ ] 다언어 공식 SDK (Swift, Kotlin)
- [ ] 외부 사용 사례 5+
- [ ] 카테고리 확장 (태블릿, 노트북, CPU)
- [ ] **마일스톤: v2.0.0**

---

## 12. GitHub Projects 운영

### 12.1 프로젝트 설정

**현재 (Phase 0~1):**
- **위치**: `github.com/[메인테이너]/TechAPI/projects` (리포 단위)
- **이름**: `TechAPI Roadmap`
- **이유**: 리포가 1개라 조직 단위 무의미

**목표 (Phase 2+):**
- **위치**: `github.com/orgs/GetTechAPI/projects`
- **범위**: 조직 전체
- **이전 시점**: `api-data` 분리할 때 (§13 트리거 참조)

### 12.2 상태 (Status) 컬럼

| 상태 | 의미 |
|---|---|
| 📋 Backlog | 아이디어 단계, 우선순위 미정 |
| 🎯 Ready | 다음 작업 준비 완료 (스펙 명확, 의존성 해결) |
| 🚧 In Progress | 진행 중 |
| 👀 In Review | PR 올라가 리뷰/테스트 중 |
| ✅ Done | 완료 |

### 12.3 커스텀 필드

| 필드 | 옵션 |
|---|---|
| **Phase** | Phase 0 · 1 · 2 · 3 · 4 · 5+ (명세서 §11과 연동) |
| **Priority** | P0 (긴급) · P1 (높음) · P2 (보통) · P3 (낮음) |
| **Category** | Backend · Data · Docs · Infra · Design · Community |
| **Size** | XS (1h) · S (반나절) · M (하루) · L (며칠) · XL (한 주+) |
| **Repo** | GitHub 자동 인식 (조직 이전 후 의미 있어짐) |

### 12.4 뷰 구성

| 뷰 이름 | 타입 | 용도 |
|---|---|---|
| **Current Sprint** | Board | Ready/In Progress/In Review만 |
| **Roadmap** | Roadmap | Phase별 타임라인 |
| **Backlog** | Table | 아이디어·우선순위 |
| **By Phase** | Board (group by Phase) | Phase별 진행도 |
| **Data Tasks** | Table (filter: Category=Data) | 데이터 작업 |
| **Bug Triage** | Table (filter: type=bug) | 버그만 |

### 12.5 이슈 라벨

```
type:bug           type:feature        type:docs
type:data          type:infra          type:refactor

priority:critical  priority:high       priority:medium

status:blocked     status:needs-info   status:good-first-issue

data:missing       data:incorrect      data:outdated
```

색상: type=파랑 / priority=빨강 / status=노랑 / data=보라

### 12.6 이슈 템플릿

`techapi/.github/ISSUE_TEMPLATE/` 안에 4종 YAML:

1. `bug_report.yml` — 버그 신고
2. `feature_request.yml` — 기능 제안
3. `data_addition.yml` — 새 기기/칩/GPU 추가 요청
4. `data_correction.yml` — 기존 데이터 정정

### 12.7 마일스톤

- `v0.1.0 - MVP` (Phase 0)
- `v0.2.0 - Data Expansion` (Phase 1)
- `v0.3.0 - Automation` (Phase 2)
- `v0.4.0 - Docs & Branding` (Phase 3)
- `v1.0.0 - Public Launch` (Phase 4)
- `v2.0.0` (Phase 5+)

### 12.8 자동화

**GitHub Project 내장**:
- 이슈 생성 → Backlog 자동 추가
- PR 링크 → In Review 이동
- PR 머지 → Done
- 이슈 close → Done

**GitHub Actions 추가**:
- `data_addition` 라벨 PR → `validate.py` 실행
- 매주 월요일 → 30일 넘은 Backlog에 `stale` 라벨
- 머지 → `api-data` 정적 JSON 자동 생성

### 12.9 운영 규칙

- 하나의 이슈 = 하나의 작업
- Size XL은 sub-issues로 쪼개기
- P0는 24시간 안에 응답
- `good-first-issue`는 Phase 1부터
- 데이터 추가 PR은 1주 안에 리뷰

### 12.10 Day 1 셋업

1. `github.com/[메인테이너]/TechAPI/projects/new`
2. 템플릿 "Roadmap" 또는 "Team planning"
3. Status 5개 컬럼
4. 커스텀 필드 4개
5. 뷰 6개
6. `.github/ISSUE_TEMPLATE/` 템플릿 4종
7. 라벨 일괄 생성 (`gh label create`)
8. 마일스톤 5~6개
9. 자동화 활성화

---

## 13. 마이그레이션 계획 (개인 → 조직)

### 13.1 왜 미래에 옮기는가

| 이유 | 영향 |
|---|---|
| 두 번째 리포 필요 (`api-data` 등) | 단일 namespace 필요 |
| 브랜드 일관성 (`GetTechAPI/techapi`) | 외부 신뢰도 ↑ |
| 외부 기여자 onboarding | 조직 단위 프로젝트 보드 활용 |
| 도메인 verified 배지 | 사기 방지, 신뢰도 |
| 협업자 추가 | 권한 관리 편리 |

### 13.2 마이그레이션 트리거 (이 중 하나 발생 시)

- 🎯 두 번째 리포를 만들 필요가 생김 (`api-data` 분리)
- 🎯 외부 기여자 첫 PR 도착
- 🎯 GitHub stars 50+ 돌파
- 🎯 도메인 `techapi.dev` 확보 + DNS 연결
- 🎯 협업자 2명 이상 추가 필요
- 🎯 Phase 2 진입

### 13.3 마이그레이션 영향 분석

| 항목 | 영향 | 처리 |
|---|---|---|
| **Git 히스토리** | 100% 보존 | 자동 |
| **이슈·PR·별·포크** | 100% 보존 | 자동 |
| **옛 URL** | 자동 리다이렉트 (영구) | 자동 |
| **Codespaces** | 기존 인스턴스 계속 동작, 신규는 새 위치 | 마이그레이션 후 새로 생성 |
| **`.devcontainer`** | 리포 따라 이동 | 자동 |
| **GitHub Actions** | 자동 이동, 시크릿은 재설정 | 시크릿 재입력 필요 |
| **로컬 `git remote`** | 수동 업데이트 권장 | `git remote set-url origin` |
| **외부 링크 (README, 트위터)** | 리다이렉트되지만 업데이트 권장 | 수동 |
| **CI/CD 외부 통합** | Webhooks 자동 이동, 일부 토큰 재발급 | 재확인 |
| **도메인 verification** | 새로 설정 | 도메인 보유시 |

### 13.4 마이그레이션 절차 (5단계)

상세 체크리스트는 **부록 D** 참조.

```
1. 사전 준비
   - 로컬 작업 commit & push
   - 외부 의존 (시크릿, webhooks) 목록화
   - 마이그레이션 알림 (있다면 사용자에게)

2. Transfer 실행
   - Settings → Danger Zone → Transfer ownership
   - New owner: GetTechAPI
   - 확인용 리포명 재입력

3. 이름 정리 (선택)
   - TechAPI → techapi (소문자) rename
   - URL 컨벤션 일치

4. 사후 정리
   - 로컬 git remote 업데이트
   - Actions 시크릿 재입력
   - Codespaces 신규 생성
   - 외부 링크 업데이트
   - 조직 프로필 README 작성

5. 검증
   - 옛 URL → 새 URL 리다이렉트 확인
   - CI/CD 정상 동작
   - 배포 파이프라인 정상
   - DB 연결 정상
```

### 13.5 롤백 계획

마이그레이션 후 문제 발생 시:

1. **Transfer 되돌리기**: 같은 절차로 다시 본인 계정으로 transfer 가능
2. **이름 되돌리기**: rename 다시
3. **시크릿 복구**: 백업해둔 .env 또는 password manager에서

마이그레이션 전 백업할 것:
- [ ] 모든 환경 변수 (.env)
- [ ] GitHub Actions secrets 목록
- [ ] 외부 통합 토큰
- [ ] 도메인 DNS 설정 (있다면)

### 13.6 마이그레이션 후 첫 주 체크

- [ ] 옛 URL → 새 URL 리다이렉트 (브라우저 직접 확인)
- [ ] `git clone` 새 URL로 정상 동작
- [ ] CI/CD 모든 파이프라인 그린
- [ ] Codespace 신규 생성 → 정상 부팅
- [ ] API 프로덕션 배포 정상
- [ ] 도메인 DNS 정상 (해당 시)
- [ ] README, 트위터, 이력서 등 외부 링크 업데이트
- [ ] 옛 위치 다른 사람이 `TechAPI` 이름 못 만들도록 placeholder 리포 만들지 않음 (리다이렉트 유지)

---

## 14. 컨벤션

### 14.1 슬러그

- **kebab-case 소문자**
- 영문 + 숫자 + 하이픈만
- 모델명 그대로: `galaxy-s25-ultra`, `snapdragon-8-elite`

### 14.2 날짜·시간

- ISO 8601 (`2025-01-22`)
- UTC 기준
- 시각 포함시 `2025-01-22T10:30:00Z`

### 14.3 단위

| 항목 | 단위 |
|---|---|
| 메모리·스토리지 | GB |
| 디스플레이 | inch |
| 무게 | gram |
| 전력 | Watt |
| 클럭 | MHz |
| 가격 | USD |
| 길이 (기기 크기) | mm |
| 화소 밀도 | PPI |

### 14.4 네이밍

| 영역 | 컨벤션 | 예 |
|---|---|---|
| Python 코드 | `snake_case` | `get_smartphone()` |
| API 필드 | `snake_case` | `release_date` |
| URL 경로 | `kebab-case` | `/smartphones/galaxy-s25` |
| 파일·폴더 | `kebab-case` | `data-models.md` |
| 환경 변수 | `SCREAMING_SNAKE` | `DATABASE_URL` |
| 브랜드 | `TitleCase` | `TechAPI`, `GetTechAPI` |
| 리포명 | `lowercase` | `techapi`, `api-data` |

### 14.5 Git 컨벤션

**브랜치:**
- `main` — 항상 배포 가능
- `feat/xxx` — 기능
- `fix/xxx` — 버그
- `data/xxx` — 데이터 추가/수정
- `docs/xxx` — 문서
- `refactor/xxx` — 리팩토링

**커밋 메시지** (Conventional Commits):
```
feat(api): add /compare endpoint
fix(scoring): correct gpu weight in performance score
data(soc): add Apple A19 Pro
docs(spec): update migration plan
refactor(db): extract benchmark to separate table
chore: bump fastapi to 0.115
```

**PR 제목**: 커밋 컨벤션과 동일

### 14.6 코드 스타일

- Python: **Black** (line length 100), **Ruff** lint, **mypy** strict
- 타입 힌트 100%
- Pydantic 모델로 입출력 모두 검증

---

## 15. 테스트 전략

### 15.1 피라미드

```
        ┌─────────────┐
        │   E2E       │  ← 적게 (~10)
        │  (실제 API  │
        │   호출)     │
        ├─────────────┤
        │ Integration │  ← 중간 (~50)
        │  (DB+API)   │
        ├─────────────┤
        │   Unit      │  ← 많이 (~200)
        │  (함수 단위)│
        └─────────────┘
```

### 15.2 도구

- **pytest** — 테스트 러너
- **httpx + TestClient** — API 통합 테스트
- **factory-boy** — 테스트 데이터 생성
- **pytest-asyncio** — async 테스트
- **coverage.py** — 커버리지 (목표 80%+)

### 15.3 데이터 검증 테스트

`scripts/validate.py`로 모든 JSON 데이터 스키마 검증:
- 필수 필드 존재
- 단위 범위 (RAM 0~64GB 등)
- FK 정합성 (soc_id가 실제 SoC를 참조하는지)
- 슬러그 컨벤션 (kebab-case, 영숫자만)

### 15.4 회귀 테스트

- API 응답 스냅샷 (deepdiff)
- 점수 계산 회귀 (algorithm_version 변경 시)
- 마이그레이션 후 데이터 정합성

### 15.5 CI 통합

모든 PR에서:
- 단위 + 통합 테스트 실행
- 커버리지 ↓되면 경고
- 데이터 검증 실행
- mypy + ruff 통과 필수

---

## 16. CI/CD

### 16.1 GitHub Actions 워크플로

| 워크플로 | 트리거 | 작업 |
|---|---|---|
| `test.yml` | PR, push | 테스트 + 린트 + 타입체크 |
| `validate-data.yml` | PR (data/ 변경) | JSON 스키마 검증 |
| `deploy-prod.yml` | push to main | Railway/Fly.io 배포 |
| `dump-data.yml` | main 머지 (data/ 변경) | api-data 리포에 정적 JSON 푸시 |
| `weekly-stale.yml` | cron (월요일) | 30일 넘은 Backlog 라벨링 |
| `release.yml` | tag (v*) | 릴리스 노트 + 패키지 배포 |

### 16.2 환경 분리

| 환경 | 도메인 | DB | 배포 트리거 |
|---|---|---|---|
| **local** | `localhost:8000` | Docker Postgres | 수동 |
| **staging** | `staging.api.techapi.dev` | Supabase (별도 프로젝트) | PR 머지 to `develop` (Phase 3+) |
| **production** | `api.techapi.dev` | Supabase 메인 | main 머지 |

### 16.3 배포 절차

```
1. main 머지
   ↓
2. test.yml 통과
   ↓
3. Docker 이미지 빌드
   ↓
4. Railway/Fly.io에 push
   ↓
5. 헬스체크 (`/v1/health` 200)
   ↓
6. 트래픽 전환 (zero-downtime)
   ↓
7. Sentry에 release 마킹
```

### 16.4 롤백

```bash
# Railway
railway rollback

# Fly.io
fly releases list
fly deploy --image registry.fly.io/techapi:v0.3.5
```

---

## 17. 운영·관측

### 17.1 로깅

- **포맷**: 구조화 JSON
- **레벨**: DEBUG (로컬), INFO (스테이징), WARN (프로덕션)
- **수집**: Better Stack 또는 Axiom (무료 티어)
- **필수 필드**: `timestamp`, `level`, `request_id`, `path`, `status`, `latency_ms`

### 17.2 모니터링

| 지표 | 도구 | 알림 임계치 |
|---|---|---|
| 에러율 | Sentry | 5min 동안 1%+ |
| 응답 시간 | Better Stack | P95 > 500ms |
| 가용성 | UptimeRobot | 5xx 또는 응답 없음 |
| DB 연결 | Supabase 대시보드 | 80% 풀 |
| 디스크 사용 | 호스팅 대시보드 | 80% |

### 17.3 알림

- **이메일**: 메인테이너 (모든 P0)
- **Discord/Slack webhook**: 빌드 실패, 배포 완료
- **GitHub Issue 자동 생성**: P0 발생 시

### 17.4 백업

| 자산 | 빈도 | 보관 | 복구 시간 목표 |
|---|---|---|---|
| Postgres | 일 1회 (Supabase 자동) | 7일 (Free) ~ 30일 (Pro) | 1시간 |
| GitHub 리포 | Git이 곧 백업 | 영구 | 10분 |
| 환경 변수 | password manager | 영구 | 5분 |
| 이미지 | GitHub | 영구 | - |

### 17.5 사고 대응 (Incident Response)

1. **감지**: 알림 수신
2. **분류**: P0 (서비스 다운) / P1 (성능 저하) / P2 (부분 장애)
3. **대응**: 롤백 우선 → 원인 분석
4. **소통**: 상태 페이지 업데이트 (Phase 3+)
5. **사후 분석**: GitHub Issue로 post-mortem 작성

---

## 18. 보안

### 18.1 시크릿 관리

- ❌ 절대 코드·Git에 commit 안 함
- ✅ `.env` (로컬, .gitignore), GitHub Actions Secrets, Railway/Fly secrets
- ✅ password manager 백업 (1Password, Bitwarden)
- ✅ Pre-commit hook으로 시크릿 누출 방지 (`gitleaks`)

### 18.2 환경 변수 카탈로그

부록 B 참조.

### 18.3 DB 보안

- Supabase RLS (Row Level Security) 활성화
- `anon` 키는 SELECT만, `service_role` 키는 메인테이너만
- IP allowlist (Phase 3+)
- 정기 비밀번호 회전 (분기)

### 18.4 API 보안

- HTTPS 강제 (HTTP → HTTPS 리다이렉트)
- CORS: 허용 도메인 명시 (`techpicks.app`, `localhost:3000`)
- 입력 검증: Pydantic 자동
- SQL Injection 방지: ORM만 사용, raw SQL 시 prepared statement
- 레이트 리밋 (**Phase 1+**, §7.6 참조)
- 토큰 검증: bcrypt 해시 저장, 평문 토큰은 DB에 저장 안 함
- 토큰은 발급 시 1회만 전체 표시, 이후 prefix만 (`tk_live_abc...`)
- 토큰 유출 대응: 24시간 grace period + 자동 회전 지원
- 의심 패턴 감지: 한 토큰이 갑자기 평소의 100배 호출 → 자동 일시정지 + 사용자 이메일 알림
- 로그에는 토큰 prefix만 기록 (전체 토큰 절대 로그 노출 X)
- 토큰 발급 횟수 제한 (계정당 active 토큰 최대 10개)

### 18.5 의존성 보안

- Dependabot 활성화 (자동 PR)
- `pip-audit` 또는 `safety` 주간 실행
- 메이저 업데이트는 수동 검토

### 18.6 책임공시 (Responsible Disclosure)

- `SECURITY.md`에 신고 방법 명시
- 이메일: `security@techapi.dev` (도메인 확보 후)
- 90일 디스클로저 정책

---

## 19. 성능 목표

### 19.1 SLO (Service Level Objectives)

| 지표 | 목표 (Phase 1) | 목표 (Phase 4+) |
|---|---|---|
| **응답 시간 (P50)** | < 200ms | < 100ms |
| **응답 시간 (P95)** | < 500ms | < 300ms |
| **응답 시간 (P99)** | < 1000ms | < 500ms |
| **가용성 (월간)** | 99.0% | 99.5% |
| **에러율** | < 1% | < 0.1% |

### 19.2 처리량 목표

| 단계 | 동시 요청 | 일 요청 |
|---|---|---|
| Phase 1 | 10 | 10K |
| Phase 3 | 100 | 100K |
| Phase 4+ | 500 | 1M |

### 19.3 최적화 전략

1. **DB 인덱스**: 슬러그, FK 컬럼, 자주 필터되는 필드
2. **응답 캐싱**: Redis (Phase 2+), CDN edge cache (Phase 3+)
3. **N+1 방지**: SQLAlchemy `selectinload`/`joinedload`
4. **정적 덤프**: 라이브 API 의존 줄임
5. **응답 압축**: gzip/brotli

---

## 20. 운영 리스크 매트릭스

| 리스크 | 가능성 | 영향 | 완화책 |
|---|---|---|---|
| 데이터 갱신 인력 부족 (1인) | 높음 | 높음 | 자동화, 기여자 모집, 우선순위 큐 |
| 스크래핑 ToS 위반 | 중간 | 높음 | 공식 스펙시트 우선, robots.txt 준수, Wikipedia 우선 |
| 점수 알고리즘 객관성 논쟁 | 중간 | 중간 | 알고리즘 오픈소스, 버전 명시, 피드백 채널 |
| 벤치마크 저작권 분쟁 | 낮음 | 높음 | Open 라이선스만 재배포, 비공개는 수치만 |
| Supabase 무료 한도 초과 | 중간 | 중간 | 정적 덤프로 트래픽 분산, Pro 전환 준비 |
| 도메인 만료 | 낮음 | 높음 | 자동 갱신, 카드 만료 알림 |
| 메인테이너 burnout | 중간 | 매우 높음 | 명확한 비목표, 자동화, 휴식 권장 |
| 데이터 정확성 오류 | 높음 | 중간 | 출처 명시, PR 리뷰, 이슈로 정정 받기 |
| 의존 서비스 장애 (Supabase 등) | 낮음 | 높음 | 정적 덤프가 폴백, 다중 호스팅 (Phase 5+) |
| 보안 사고 (API 키 유출 등) | 낮음 | 높음 | 시크릿 스캔, 정기 회전, 모니터링 |

---

## 21. 커뮤니티·기여

### 21.1 기여자 정책

- 어떤 기여든 환영 (코드·데이터·문서·이슈·버그 리포)
- CLA(Contributor License Agreement) 없음 → 기여자 친화
- 데이터 기여는 `CONTRIBUTORS.md`에 자동 기록

### 21.2 커뮤니케이션 채널

| 채널 | 용도 | 시점 |
|---|---|---|
| GitHub Issues | 버그·기능 제안·데이터 요청 | 처음부터 |
| GitHub Discussions | 일반 Q&A, 아이디어 | Phase 2+ |
| Discord (선택) | 실시간 채팅 | Phase 3+ |
| 트위터/블루스카이 | 업데이트 공지 | Phase 3+ |

### 21.3 Code of Conduct

- Contributor Covenant 2.1 채택
- `CODE_OF_CONDUCT.md`에 명시
- 위반 신고: `conduct@techapi.dev`

### 21.4 메인테이너 정책

| 역할 | 권한 |
|---|---|
| Maintainer | merge, release, settings |
| Trusted Contributor | 머지는 못하지만 우선 리뷰 |
| Contributor | PR, 이슈 가능 |

### 21.5 릴리스 정책

- Semantic Versioning (SemVer)
- 모든 릴리스 → GitHub Release + CHANGELOG.md
- Breaking change는 메이저 버전, 12개월 deprecation 기간

---

## 22. 향후 전략

### 22.1 비즈니스 모델

**원칙**: 오픈소스 + 무료 등록 + 점진적 티어. 핵심 데이터는 영구 무료.

#### 모델 (TMDB 참고)

```
무료 (Free, Hobby, OSS)  ← 95% 사용자, 가치 제공이 핵심
        ↓
Commercial 유료 ($19/월) ← 운영 비용 보조 (Phase 5+, 선택)
        ↓
Self-hosting 가능        ← 토큰 거부하면 직접 호스팅
```

#### 수익화 가능성 (선택 사항, Phase 5+에서만 검토)

- **GitHub Sponsors** — 개인 후원 (처음부터 가능)
- **Open Collective** — 투명한 후원금
- **Commercial 티어** — 상업 사용자 $19/월 (운영비 보조)
- **데이터 라이선싱** — 대기업이 CC-BY-SA 면제 요청 시 협상

#### 절대 안 함

- ❌ 광고
- ❌ 데이터 자체 판매
- ❌ 무료 티어 폐쇄
- ❌ 핵심 데이터 유료화
- ❌ 토큰 시스템 폐쇄 소스화

#### 지속 가능성 시나리오

| 시나리오 | 운영 자금원 |
|---|---|
| **베이스라인** | 메인테이너 자비 (~$30/월) |
| **이상적** | Sponsors + Commercial 티어로 호스팅비 + 도메인 충당 |
| **최악** | 정적 덤프만 유지, 라이브 API 일시 중단 (코드·데이터는 영구 보존) |

오픈소스가 보험. **TechAPI가 운영 안 돼도 사용자는 self-host로 살아남음.**

### 22.2 TechPicks 및 다른 사용자와의 관계

TechAPI는 **공공 데이터 플랫폼**이고, TechPicks는 **그 위에 올라가는 여러 앱 중 하나** (첫 사용자).

```
       ┌─────────────────────────────────┐
       │           TechAPI               │
       │  (소비자 전자기기 스펙 플랫폼)   │
       └────────────┬────────────────────┘
                    │
        ┌───────────┼───────────┬──────────┬───────────┐
        ▼           ▼           ▼          ▼           ▼
  ┌──────────┐ ┌────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐
  │TechPicks │ │ 가격   │ │ 리뷰     │ │  AI    │ │ 학술     │
  │  (앱)    │ │ 추적   │ │ 미디어   │ │ 에이전트│ │ 연구     │
  └──────────┘ └────────┘ └──────────┘ └────────┘ └──────────┘
```

**잠재 사용자 타깃:**
- 📱 소비자 모바일·웹 앱 (TechPicks, 가격비교, 추천 봇)
- 📊 데이터 분석가·블로거·미디어
- 🤖 AI 에이전트·챗봇 (MCP 서버로 확장 가능, Phase 5+)
- 🎓 학생 프로젝트·학술 연구
- 🏢 사내 도구 (회사가 디바이스 자산 관리)
- 🛠️ 개발자 도구 (스펙 비교 IDE 플러그인 등)

**TechPicks의 특별한 역할: Reference Consumer**

TechPicks는 단순한 첫 사용자가 아니라 **reference consumer**:
- TechAPI 설계가 실제 앱 요구를 충족하는지 검증
- 빈틈을 가장 먼저 발견하고 이슈로 제기
- 새 기능의 첫 테스트베드
- 다른 사용자가 참고할 수 있는 살아있는 예시

하지만 **TechPicks의 요구가 TechAPI 설계를 일방적으로 좌우하지 않음.** TechPicks가 필요로 하는 모든 기능이 TechAPI에 들어가는 게 아니라:
- 일반화 가능한 기능 → TechAPI
- TechPicks-specific 로직 → TechPicks 내부

**TechPicks 마이그레이션 단계:**

```
Phase 0~3: TechPicks 자체 백엔드 + TechAPI 외부 사용자용 별도 운영
Phase 4:   TechPicks가 TechAPI로 점진 마이그레이션
Phase 5+:  TechPicks 풀스택 TechAPI 의존
```

이 단계는 TechAPI가 외부 사용자에게도 안정적으로 제공된 다음에 진행. TechPicks가 너무 빨리 의존하면 외부 사용자가 보기엔 "TechPicks 전용 백엔드"처럼 보일 위험.

### 22.3 외부 사용자 유치 (Multi-Consumer 전략)

TechAPI의 **핵심 목표 중 하나**. TechPicks 외에 다양한 앱·플랫폼·도구가 사용하도록.

**카테고리별 유치 전략:**

| 사용자 카테고리 | 가치 제안 | 유치 채널 |
|---|---|---|
| 모바일/웹 앱 개발자 | 무료, 무인증, 풍부한 데이터 | Show HN, ProductHunt, dev.to |
| 가격비교 사이트 | 스펙 데이터 안정적 소스 | 직접 컨택, 파트너십 |
| 리뷰 블로그·미디어 | 스펙 표·점수 임베드용 | iframe 위젯 (Phase 4+) |
| AI 에이전트·챗봇 | MCP 서버로 즉시 통합 | MCP Directory 등록 (Phase 5+) |
| 학생·연구자 | 무료 + 정적 JSON 다운로드 | 학회·해커톤 후원 |
| 사내 도구 개발자 | 자산 관리·구매 결정 지원 | LinkedIn, 기업 컨택 |
| IDE/터미널 도구 | 개발자 워크플로 통합 | CLI 도구·VSCode 익스텐션 |

**마일스톤별 외부 사용자 목표:**
- Phase 3: 외부 사용자 1+ (TechPicks 외)
- Phase 4: 외부 사용자 5+
- Phase 5: 외부 사용자 20+, 사용 사례 모음 (`USERS.md`)

**제공 자산:**
- 풍부한 OpenAPI 문서 (`techapi.dev`)
- 임베드 가능한 비교 위젯 (Phase 4+)
- 다언어 SDK (Phase 4+)
- MCP 서버 (Phase 5+) — AI 에이전트 즉시 통합
- "Built with TechAPI" 배지

**유치 안 할 영역:**
- 데이터 자체를 재판매하려는 경쟁자 (CC-BY-SA 위반)
- 광고만 끼워파는 래퍼 사이트
- 데이터 출처 표기 안 하는 사용자

### 22.4 데이터 파트너십

- 제조사 공식 데이터 피드 (Phase 5+, 큰 꿈)
- 벤치마크 단체와의 협업 (Blender Foundation 등)
- 학술 연구자에게 데이터 덤프 제공

### 22.5 확장 가능성

- **수직 확장**: 카테고리 추가 (태블릿, 노트북…)
- **수평 확장**: 언어 추가 (ko, ja, zh)
- **시간 확장**: 시계열 (가격 변동, 펌웨어 업데이트)
- **깊이 확장**: 자체 벤치마크, 사용자 측정

---

## 23. 의사결정 로그 (ADR)

주요 결정사항과 근거. 새 결정은 이 섹션에 append.

### ADR-001: 백엔드는 FastAPI (Python)
- **날짜**: 2026-05-26
- **상태**: Accepted
- **결정**: FastAPI 사용
- **대안**: NestJS, Spring Boot, Gin
- **근거**: 빠른 개발 속도, 자동 OpenAPI, async, 학습 곡선 낮음, 솔로 개발자 친화

### ADR-002: DB는 Supabase Postgres
- **날짜**: 2026-05-26
- **상태**: Accepted
- **결정**: Supabase 호스팅 Postgres
- **대안**: 자체 호스팅 Postgres, MySQL, MongoDB
- **근거**: 무료 티어 충분, 운영 부담 적음, RLS 활용 가능, 어드민 UI 호환

### ADR-003: 단일 리포 → 점진 분리
- **날짜**: 2026-05-26
- **상태**: Accepted
- **결정**: Phase 0~1은 단일 리포, Phase 2부터 분리
- **대안**: 처음부터 다중 리포로 분리
- **근거**: 솔로 개발자의 리포 관리 부담, YAGNI 원칙, 필요해질 때 분리

### ADR-004: 개인 계정 리포 유지 → 미래 마이그레이션
- **날짜**: 2026-05-26
- **상태**: Accepted
- **결정**: Phase 0~1 동안 개인 계정 `TechAPI` 유지, Phase 2 진입 시 `GetTechAPI/techapi`로 이전
- **대안**: 지금 즉시 조직으로 이전
- **근거**: Codespaces 셋업 마이그레이션 비용 회피, GitHub 자동 리다이렉트로 미래 비용 0

### ADR-005: 데이터 라이선스 CC-BY-SA 4.0
- **날짜**: 2026-05-26
- **상태**: Accepted
- **결정**: 데이터는 CC-BY-SA, 코드는 MIT
- **대안**: CC0, ODbL, 자체 라이선스
- **근거**: OpenStreetMap·MusicBrainz 검증 모델, 데이터 생태계 보호, 상업 이용 허용

### ADR-006: 비공개 벤치마크 수치는 알고리즘 입력만
- **날짜**: 2026-05-26
- **상태**: Accepted
- **결정**: Geekbench·AnTuTu 점수는 저장하되 API로 직접 노출 안 함
- **대안**: 전혀 사용 안 함 / 그대로 재배포
- **근거**: 법적 안전 + 점수 계산 유용성 둘 다 확보

### ADR-007: 솔로 단계 GitHub Project는 리포 단위
- **날짜**: 2026-05-26
- **상태**: Accepted
- **결정**: Phase 0~1은 `[메인테이너]/TechAPI/projects`, Phase 2부터 조직 단위로 이전
- **근거**: 리포 1개 상황에서 조직 단위는 오버엔지니어링

### ADR-008: TechAPI는 플랫폼, TechPicks 전용 백엔드 아님
- **날짜**: 2026-05-26
- **상태**: Accepted
- **결정**: TechAPI는 다중 사용자(앱·웹·AI 에이전트·연구자)를 위한 공공 데이터 플랫폼. TechPicks는 첫 사용자이자 reference consumer일 뿐.
- **대안**: TechPicks 백엔드로만 만들고 부가적으로 공개
- **근거**:
  - 처음부터 다중 사용자를 가정하면 API 설계가 더 일반화·견고해짐
  - 데이터 라이선스(CC-BY-SA)가 다중 사용을 전제
  - 공공 데이터 API 모델은 공공 인프라 발상이지 특정 앱의 백엔드가 아님
  - 외부 사용자가 곧 데이터 정확성·기능 풍부함의 검증자
  - TechPicks 시장 실패 시에도 TechAPI는 독립적으로 가치 보유
- **영향**:
  - TechPicks-specific 기능 요청 거부됨
  - API 안정성·문서 품질이 internal velocity보다 우선
  - 외부 사용자 유치가 Phase 3 핵심 목표
  - TechPicks 마이그레이션은 외부 사용자 안정화 이후

### ADR-009: TMDB식 토큰 기반 접근 + 오픈소스 self-host 옵션
- **날짜**: 2026-05-26
- **상태**: Accepted
- **결정**: 완전 익명 접근 대신, TMDB식 **무료 등록 + 토큰 발급 + 티어 한도** 모델 채택. 단, 코드 100% 오픈소스 유지하여 self-host 옵션 제공.
- **대안 1**: 완전 익명 (IP 기반 제한만)
- **대안 2**: 전부 유료 (Stripe API식)
- **근거**:
  - **사용 추적**: 누가 뭘 쓰는지 알아야 데이터 우선순위 결정 가능
  - **악용 방지**: 남용 시 IP 차단보다 토큰 차단이 정밀
  - **점진적 티어링**: Free → Hobby → OSS → Commercial 가능
  - **사용자 관계**: 이메일로 breaking change 통보 등
  - **재정 지속성**: Commercial 티어로 운영비 보조 (Phase 5+ 옵션)
  - **오픈소스 정신 보존**: 코드 공개 + self-host 가능
- **영향**:
  - Phase 1에 토큰 시스템 구축 필요 (가입·발급·미들웨어)
  - 대시보드 사이트 구축 (Phase 3)
  - Self-hosting 가이드 (`docs/SELF_HOSTING.md`) 작성 필수
  - 정적 JSON 덤프는 항상 무인증
- **참고 모델**: TMDB API, OpenWeather, Stripe (티어링 부분만)

### ADR-010: 전용 서버 (FastAPI on Railway/Fly.io) — 서버리스/Next.js 대신
- **날짜**: 2026-05-26
- **상태**: Accepted
- **결정**: FastAPI를 Railway 또는 Fly.io에 배포하는 **전용 서버 모델**. Next.js 풀스택 / 정적 / Cloudflare Workers / Vercel Serverless 등 대안은 모두 검토 후 비채택.
- **검토한 대안**:
  - **정적 덤프 단독**: 인증·복잡 쿼리 불가 → 핵심 요구 불충족
  - **Next.js + Vercel 서버리스**: cold start, DB 풀 폭주, 백그라운드 작업 불가, vendor lock-in, 비용 변동성 → 백엔드 용도로 업계가 권장하지 않음
  - **Cloudflare Workers + Hono**: Workers 한계 (Postgres 직결 어려움, 일부 Node API 불가) + 별도 학습 부담
  - **자체 VPS (DigitalOcean Droplet)**: 운영 부담 (SSL·모니터링·재시작 직접 설정) — 솔로 부담
- **근거**:
  - **속도 + 동적 = 전용 서버**가 백엔드 업계의 검증된 답
  - **Cold start 없음**: 응답 시간 일관 (P95 50ms 이하)
  - **DB 연결 재사용**: 풀 폭주 없음, PgBouncer 추가 불필요
  - **백그라운드 작업 자유**: 워커 큐·스크래핑·점수 재계산 모두 가능
  - **메모리 캐시 유효**: 요청 간 상태 공유 가능
  - **비용 예측**: $5/월 고정 (Railway) — 트래픽 변동에 무관
  - **백엔드 학습 가치 최대**: FastAPI는 시장 표준
  - **Vendor lock-in 없음**: Docker 이미지로 어디든 이전 가능
  - **단일 VPS로 충분**: 정적 덤프 + 가벼운 API는 작은 서버 한 대로 운영 가능
  - **Railway/Fly.io의 모던 PaaS**: git push → 자동 배포, SSL·health check·모니터링 자동
- **운영 부담의 현실**:
  - 실제 작업: 가끔 대시보드 확인 + 월 1회 dependency 업데이트
  - 모던 PaaS는 SSL/재시작/로그 자동
  - "서버 운영 어렵다"는 옛 VPS 시절 기억
- **영향**:
  - §0.5, §4, §5, §16 등 명세서 전체가 이 결정 기준으로 작성됨
  - TechPicks 앱은 별도 프로젝트로 Next.js+Vercel 자유 채택 가능
  - markdown-rbmk(Vercel)와 다른 스택 — 각 프로젝트 특성에 맞는 도구
  - Phase 4+ 트래픽 폭증 시 정적 마이그레이션 옵션 보존 (api-data 리포로 일부 엔드포인트 전환 가능)
- **재검토 트리거**: Phase 4+에서 월 비용 $50+ 또는 일 트래픽 100만 도달 시 정적+서버 하이브리드 검토

### ADR-011: 컴퓨터 CPU·GPU 카테고리 조기 도입

- **날짜**: 2026-05-27
- **상태**: Accepted
- **결정**: 데스크탑/랩탑 **CPU**(Intel Core, AMD Ryzen 등)를 별도 엔티티(`CPU`, §6.7)로 추가하고 `/cpus`·`/cpus/{slug}` 엔드포인트를 제공. **Discrete GPU**(§6.5, v1 스코프 P1)도 데이터·엔드포인트(`/gpus`)를 함께 활성화.
- **대안**: v2+까지 미루기 (원래 §3.2 로드맵), 또는 SoC에 욱여넣기
- **근거**:
  - 메인테이너가 "전 세계 폰·칩셋 + 컴퓨터 칩셋까지 전부" 데이터화를 요청
  - GPU는 이미 §6.5에 모델이 존재 → 엔드포인트만 노출하면 됨
  - CPU는 모바일 SoC와 스펙 축(소켓·코어 구성·TDP·캐시)이 달라 별도 엔티티가 적절
  - 데이터 정확성 원칙(§1.6) 유지: 실제 출시 모델 + source_urls만 수록, 가상의 "전 세계 모든 모델" 날조 금지
- **영향**:
  - `CPU` 모델·스키마·라우터·시드/검증·테스트 추가
  - 원시 벤치마크(Cinebench/Geekbench)는 ADR-006대로 API 미노출, 알고리즘 입력으로만 보존
  - CPU/GPU용 점수 알고리즘은 Phase 1로 연기 (현재는 스펙 데이터만 제공)
  - 데이터는 출처 가능 범위에서 배치로 지속 확장

---

## 24. 용어집

| 용어 | 정의 |
|---|---|
| **SoC** | System-on-Chip. CPU·GPU·모뎀 등이 하나의 칩에 통합된 시스템. 스마트폰의 두뇌. (Snapdragon, Exynos, A18 Pro 등) |
| **NPU** | Neural Processing Unit. AI 연산 전용 가속기 |
| **TOPS** | Tera Operations Per Second. NPU 성능 지표 |
| **Discrete GPU** | 독립 그래픽 카드 (RTX 5090 등). 통합 GPU와 대비 |
| **MSRP** | Manufacturer's Suggested Retail Price. 제조사 권장 소비자가 |
| **Slug** | URL 친화 식별자. `galaxy-s25` 같은 kebab-case |
| **JSONB** | Postgres의 바이너리 JSON 타입. 인덱싱·쿼리 가능 |
| **RLS** | Row Level Security. Postgres 행 단위 권한 |
| **ORM** | Object-Relational Mapping |
| **SLO** | Service Level Objective. 운영 목표 |
| **ADR** | Architecture Decision Record. 의사결정 기록 |
| **MVP** | Minimum Viable Product |
| **CC-BY-SA** | Creative Commons 저작자표시-동일조건변경허락 |
| **YAGNI** | You Aren't Gonna Need It. 미리 만들지 말라는 원칙 |
| **PR** | Pull Request |
| **CI/CD** | Continuous Integration / Continuous Deployment |

---

## 25. 참고자료

### 25.1 영감

- [OpenStreetMap](https://www.openstreetmap.org) — 데이터 라이선스
- [MusicBrainz](https://musicbrainz.org) — 데이터 모델·기여 시스템
- [The Movie Database (TMDB)](https://www.themoviedb.org) — API 설계
- [Wikidata](https://www.wikidata.org) — 구조화 데이터

### 25.2 도구

- [FastAPI](https://fastapi.tiangolo.com) — 백엔드
- [SQLModel](https://sqlmodel.tiangolo.com) — ORM
- [Supabase](https://supabase.com) — DB 호스팅
- [Scalar](https://scalar.com) — API 문서
- [Railway](https://railway.app) / [Fly.io](https://fly.io) — 배포

### 25.3 가이드

- [REST API Design Best Practices](https://restfulapi.net)
- [Twelve-Factor App](https://12factor.net)
- [Semantic Versioning](https://semver.org)
- [Conventional Commits](https://www.conventionalcommits.org)
- [Keep a Changelog](https://keepachangelog.com)
- [Choose a License](https://choosealicense.com)

### 25.4 추천 읽을거리

- "Designing Data-Intensive Applications" — Martin Kleppmann
- "API Design Patterns" — JJ Geewax
- "Domain-Driven Design Distilled" — Vaughn Vernon

---

# 부록 A: Day 1 To-Do

1. [x] `GetTechAPI` 조직 생성 (예약)
2. [x] `[메인테이너]/TechAPI` 개인 리포 생성
3. [x] Codespaces 셋업
4. [ ] 이 명세서를 리포 `docs/SPEC.md`로 커밋
5. [ ] `[메인테이너]/TechAPI/projects` → New project (`TechAPI Roadmap`) + 라벨·필드·뷰 셋업
6. [ ] `.github/profile/README.md` (조직 페이지) 작성 — Phase 2까지 placeholder
7. [ ] dbdiagram.io에 ERD 그리기 (Brand, SoC, Smartphone, GPU)
8. [ ] Supabase 프로젝트 생성 → 마이그레이션 1회
9. [ ] FastAPI 초기 셋업 → `GET /v1/health` 동작 확인
10. [ ] `data/smartphones/galaxy-s25.json` 한 건 작성
11. [ ] `scripts/seed.py`로 DB 주입 → `GET /v1/smartphones/galaxy-s25` 확인
12. [ ] README, LICENSE (MIT), .gitignore, .env.example 셋업

이 12개가 끝나면 **TechAPI는 살아있는 프로젝트**입니다.

---

# 부록 B: 환경 변수 카탈로그

`.env.example`:

```bash
# === Database ===
DATABASE_URL=postgresql://user:pass@host:5432/dbname
DATABASE_POOL_SIZE=10

# === Supabase ===
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...   # 시크릿, 절대 클라이언트 노출 X

# === API ===
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=development           # development | staging | production
API_BASE_URL=http://localhost:8000

# === Security ===
SECRET_KEY=...                # JWT/세션 (Phase 4+)
CORS_ORIGINS=http://localhost:3000,https://techpicks.app

# === Logging ===
LOG_LEVEL=INFO
SENTRY_DSN=https://...        # 선택

# === External Services ===
REDIS_URL=redis://localhost:6379    # 선택 (Phase 2+)

# === Scoring ===
SCORING_CONFIG_PATH=./config/scoring.yaml
```

⚠️ `.env`는 절대 git에 commit하지 마세요. `.gitignore`에 포함 확인.

---

# 부록 C: API 응답 전체 예시

### GET `/v1/smartphones/galaxy-s25?include=soc,brand`

```json
{
  "id": 12,
  "slug": "galaxy-s25",
  "name": "Galaxy S25",
  "brand": {
    "id": 1,
    "slug": "samsung",
    "name": "Samsung",
    "country": "KR",
    "url": "/v1/brands/samsung"
  },
  "soc": {
    "id": 27,
    "slug": "snapdragon-8-elite",
    "name": "Snapdragon 8 Elite",
    "manufacturer": {
      "slug": "qualcomm",
      "name": "Qualcomm",
      "url": "/v1/brands/qualcomm"
    },
    "process_nm": 3.0,
    "gpu_name": "Adreno 830",
    "url": "/v1/socs/snapdragon-8-elite"
  },
  "release_date": "2025-01-22",
  "msrp_usd": 999,
  "ram_gb": 12,
  "storage_options_gb": [128, 256, 512],
  "display": {
    "size_inch": 6.2,
    "resolution": "3120x1440",
    "refresh_hz": 120,
    "type": "Dynamic AMOLED 2X",
    "brightness_nits": 2600,
    "ppi": 505
  },
  "cameras": [
    {
      "type": "main",
      "mp": 50,
      "aperture": 1.8,
      "ois": true,
      "sensor": "Samsung GN3"
    },
    {
      "type": "ultrawide",
      "mp": 12,
      "aperture": 2.2,
      "ois": false
    },
    {
      "type": "telephoto",
      "mp": 10,
      "aperture": 2.4,
      "ois": true,
      "optical_zoom": 3
    },
    {
      "type": "selfie",
      "mp": 12,
      "aperture": 2.2
    }
  ],
  "battery_mah": 4000,
  "charging_wired_w": 25,
  "charging_wireless_w": 15,
  "weight_g": 162.0,
  "dimensions": {
    "height_mm": 146.9,
    "width_mm": 70.5,
    "depth_mm": 7.2
  },
  "ip_rating": "IP68",
  "os": "Android",
  "os_version": "15",
  "connectivity": {
    "wifi": "Wi-Fi 7",
    "bluetooth": "5.4",
    "nfc": true,
    "usb": "USB-C 3.2"
  },
  "image_url": "https://cdn.jsdelivr.net/gh/GetTechAPI/images/smartphones/galaxy-s25.webp",
  "score": {
    "algorithm_version": "1.0.0",
    "overall": 87.4,
    "performance": 92.1,
    "camera": 88.5,
    "battery": 81.2,
    "display": 90.0,
    "value": 85.3
  },
  "verified": true,
  "source_urls": [
    "https://samsung.com/galaxy-s25/specs",
    "https://en.wikipedia.org/wiki/Samsung_Galaxy_S25"
  ],
  "created_at": "2025-01-25T12:00:00Z",
  "updated_at": "2025-03-10T08:30:00Z"
}
```

---

# 부록 D: 조직 마이그레이션 체크리스트

Phase 2 진입 시 `[메인테이너]/TechAPI` → `GetTechAPI/techapi` 이전 절차.

### D.1 사전 (1일 전)
- [ ] 모든 로컬 변경 commit + push
- [ ] 환경 변수 백업 (password manager)
- [ ] GitHub Actions Secrets 목록 작성
- [ ] 외부 통합 (webhooks) 목록 작성
- [ ] 도메인·DNS 백업 (있다면)
- [ ] 마이그레이션 알림 (있다면 사용자/기여자에게)

### D.2 Transfer 실행 (10분)
- [ ] `github.com/[메인테이너]/TechAPI/settings` 접속
- [ ] (선택) Repository name: `TechAPI` → `techapi` rename
- [ ] 페이지 하단 Danger Zone → Transfer ownership
- [ ] New owner: `GetTechAPI` 입력
- [ ] 확인용 리포명 재입력
- [ ] Transfer 클릭 → 완료

### D.3 사후 정리 (1시간)
- [ ] 로컬: `git remote set-url origin https://github.com/GetTechAPI/techapi.git`
- [ ] `git remote -v`로 확인
- [ ] GitHub Actions Secrets 재입력 (전부 복사)
- [ ] 외부 통합 webhooks 재설정 (Discord, Slack 등)
- [ ] Codespaces 신규 생성 → devcontainer 정상 동작 확인
- [ ] Railway/Fly 배포 시크릿 GitHub 연결 갱신
- [ ] 도메인 DNS / verified 도메인 재설정 (조직 settings)

### D.4 검증 (당일)
- [ ] 옛 URL 접속 → 새 URL로 자동 리다이렉트 확인
- [ ] `git clone https://github.com/GetTechAPI/techapi.git` 정상
- [ ] PR 새로 만들기 → CI 정상 동작
- [ ] 프로덕션 배포 정상 (`/v1/health` 200)
- [ ] DB 연결 정상
- [ ] Sentry/모니터링 정상 보고

### D.5 외부 업데이트 (1주일 안에)
- [ ] README의 모든 옛 URL 업데이트
- [ ] 다른 리포에서 참조 업데이트
- [ ] 트위터/블루스카이 프로필
- [ ] 개인 이력서·포트폴리오
- [ ] 외부 글·블로그에서 링크 업데이트
- [ ] 패키지 매니페스트 (PyPI 등, Phase 4+)

### D.6 마무리
- [ ] 조직 프로필 README 본격 작성 (`.github/profile/README.md`)
- [ ] `api-data` 등 두 번째 리포 분리 작업 시작
- [ ] ADR-004 → "Completed" 상태로 업데이트
- [ ] 명세서 §5.1을 "현재"가 아닌 "과거"로 마킹

---

**문서 끝**

| | |
|---|---|
| **버전** | v1.0 — Ready for implementation |
| **다음 검토** | Phase 1 진입 시 |
| **라이선스** | CC-BY 4.0 |
