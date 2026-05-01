# skill-creator-strict

스킬을 schema-first로 짜고, stage가 넘어갈 때마다 validator가 통과시킴. 다단계 실행이 들어가는 스킬용으로 [`anthropics/skills/skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator)를 대체할 수 있게 만든 도구.

[English README](./README.md)

## Why

`skill-creator`는 stage 사이 데이터 계약을 산문으로 강제함. 산문이 실패하는 순간 — 가령 `grading.json`에 `text`/`passed` 대신 `name`/`met` 같은 v1 흔적이 남아 있을 때 — 다음 stage가 그걸 그대로 먹고 넘어감. 결국 viewer 렌더 시점이나 사람이 리뷰할 때에야 문제가 드러남.

`skill-creator-strict`는 그 계약을 JSON Schema로 옮기고, stage 경계마다 validator를 끼움. 잘못된 데이터는 source에서 바로 막히고, 어느 필드가 깨졌는지 구조적 에러로 짚어줌.

## Install

```bash
git clone https://github.com/<owner>/skill-creator-strict
cd skill-creator-strict
python -m venv .venv
.venv/bin/pip install jsonschema
```

## Quick start

```bash
# 새 스킬 부트스트랩
python -m scripts.new_skill my-skill --type pipeline --path ~/skills

# stage 사이 파일 하나 검증
python -m scripts.validate <schema_name> path/to/file.json
# schema name: workflow | evals | grading | benchmark | feedback | trigger_eval

# 워크스페이스 전체 검증
python -m scripts.preflight ~/skills/my-skill-workspace

# Run 결과를 benchmark로 집계
python -m scripts.aggregate_benchmark <iteration_dir> --skill-name my-skill

# 배포용 패키징
python -m scripts.package_skill ~/skills/my-skill
```

런타임 LLM이 따라가는 runbook은 [`SKILL.md`](./SKILL.md)에 있음.

## skill-creator와 무엇이 다른가

| | `skill-creator` | `skill-creator-strict` |
|---|---|---|
| 문서 분리 | `SKILL.md` 하나에 런타임 + 저자 지침이 섞여 있음 | `SKILL.md`(런타임) + `AUTHORING.md`(저자)로 분리 |
| Stage 사이 계약 | 산문 명령 | JSON Schema (draft 2020-12) |
| Stage 전환 | LLM이 판단 | Validator-gated. 잘못된 입력은 거부 |
| Run 상태 | 디렉토리 컨벤션 + flat `history.json` | iteration별 stage record가 들어간 `workflow_state.json` |
| 스킬 타입 | 한 가지 모양(암묵적) | `narrative` / `pipeline`(명시적) |
| 부트스트랩 | 수동으로 파일 생성 | `scripts.new_skill` CLI |
| Preflight | 없음 | `scripts.preflight <workspace>` |

## skill-creator에서 그대로 가져온 것

브라우저 기반 eval viewer, description 최적화 loop, 그리고 보조 스크립트들(`run_loop.py`, `improve_description.py`, `run_eval.py`, `generate_report.py`, `utils.py`, `eval-viewer/*`, `assets/*`)은 upstream과 byte-identical로 가져옴. upstream 쪽 패치가 그대로 흘러들어옴. validator-gating으로 측정 가능한 개선이 생기는 부분만 fork함.

## 디렉토리 구조 — skill-creator와 나란히 놓고 보기

### `anthropics/skills/skill-creator`

```
skill-creator/
├── SKILL.md
├── LICENSE.txt
├── agents/
│   ├── analyzer.md
│   ├── comparator.md
│   └── grader.md
├── assets/
│   └── eval_review.html
├── eval-viewer/
│   ├── generate_review.py
│   └── viewer.html
├── references/
│   └── schemas.md                  ← JSON 형태를 산문으로 적어둠
└── scripts/
    ├── aggregate_benchmark.py
    ├── generate_report.py
    ├── improve_description.py
    ├── package_skill.py
    ├── quick_validate.py           ← ad-hoc 구조 체크
    ├── run_eval.py
    ├── run_loop.py
    └── utils.py
```

### `skill-creator-strict`

```
skill-creator-strict/
├── SKILL.md
├── AUTHORING.md                         NEW   저자 노트 (런타임에서 분리)
├── README.md / README.ko.md
├── LICENSE
├── agents/
│   ├── analyzer.md / comparator.md / grader.md
├── assets/
│   └── eval_review.html            carryover
├── docs/
│   └── design-rationale.md         NEW   설계 결정 history
├── eval-viewer/
│   ├── generate_review.py          carryover
│   └── viewer.html                 carryover
├── evals/
│   └── evals.json                  NEW   regression 코퍼스
├── schemas/                        NEW   v1 references/schemas.md 대체 (산문 → JSON Schema)
│   ├── workflow.schema.json
│   ├── evals.schema.json
│   ├── grading.schema.json
│   ├── benchmark.schema.json
│   ├── feedback.schema.json
│   └── trigger_eval.schema.json
├── scripts/
│   ├── validate.py                 NEW   schema 기반 validator (quick_validate 대체)
│   ├── workflow_state.py           NEW   manifest API
│   ├── new_skill.py                NEW   부트스트랩 CLI
│   ├── preflight.py                NEW   워크스페이스 전체 검증
│   ├── aggregate_benchmark.py      FORK  + 입출력 validator hook
│   ├── package_skill.py            FORK  + AUTHORING.md 인지, workflow_state.json 제외
│   ├── run_loop.py                 carryover
│   ├── improve_description.py      carryover
│   ├── run_eval.py                 carryover
│   ├── generate_report.py          carryover
│   └── utils.py                    carryover
└── stages/
    └── README.md                   NEW   pipeline 스킬용 stage-script 계약
```

**한눈에:**
- 새 top-level 5개 (`AUTHORING.md`, `docs/`, `evals/`, `schemas/`, `stages/`)
- 새 스크립트 4개, fork 2개, 그대로 가져온 것 5개
- `references/schemas.md`(산문)을 `schemas/*.schema.json`(검증 가능한 계약)으로 교체
- `agents/`, `assets/`, `eval-viewer/`는 손 안 댐

## 문서

- [`SKILL.md`](./SKILL.md) — 런타임 runbook
- [`AUTHORING.md`](./AUTHORING.md) — 저자 컨벤션
- [`docs/design-rationale.md`](./docs/design-rationale.md) — 설계 결정과 트레이드오프
- [`stages/README.md`](./stages/README.md) — pipeline 스킬용 stage-script 계약

## 호환성

- Python 3.11+
- `jsonschema >= 4.0`
- 스킬 소비자: Claude Code, Claude.ai, Cowork (환경별 주의사항은 SKILL.md 참고)

## 라이선스

[MIT](./LICENSE)

## 저자 원칙

스킬에는 네 가지 저자 원칙도 같이 박혀 있음 — *think before coding*, *simplicity first*, *surgical changes*, *goal-driven execution*. 각 stage 안에 녹여놨고, 매핑은 [`docs/design-rationale.md`](./docs/design-rationale.md#decision-10)에서 확인.

## Acknowledgements

[`anthropics/skills/skill-creator`](https://github.com/anthropics/skills/tree/main/skills/skill-creator)의 설계와 코드를 상당 부분 가져와 그 위에 얹어 만들었음.
