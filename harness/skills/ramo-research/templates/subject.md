---
type: Research Topic
title: "<대상 이름> 구조"
kind: subject
summary: <one line for the overview table: what this is and its defining design choice>
category: research
status: draft
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
tags: <topic-tag>, <domain-tag>
generated: { by: ramo-research/<model-id>, at: <ISO-8601> }
stale_after: <updated + 12 months, YYYY-MM-DD>
---


<!-- 저작 안내 (확정 전 이 주석 블록을 지움)
규범 전문: .claude/rules/workflow/00-research.md, 가독성: .claude/rules/common/doc-readability.md
  - 대상 하나(코드베이스, 논문 하나, 시스템 하나)를 처음 보는 사람이 10분 안에 구조를 잡게 쓰는 문서임
  - 문장보다 그림과 표. 절마다 표 하나나 다이어그램 하나가 중심이고 글은 그 앞뒤 2-3문장
  - 주장마다 위치를 붙임. 표는 `위치` 열, 문장은 끝 괄호 (코드: 경로 또는 file::symbol, 논문: §·Table)
  - 출처 id(s01 ...)는 문장이나 표 칸에 그대로 적어 `출처` 표와 이어지게 함
  - 수치는 조건(지표 정의, 데이터, 비교 대상)과 함께. 읽는 이의 해석은 `(해석)` 으로 시작
  - 더 자세한 내용은 원천 소스와 후속 리서치의 몫임. 여기서는 핵심 구조만, 문서 기준선 약 150행
  - `##` 만 씀
-->

# <대상 이름> 구조

<2-3 sentences: what the subject does, and the one design choice a reader must remember.> (s01)

## 전체 아키텍처

```text
<a box-and-arrow diagram of the whole flow: data → features → model(s) → output.
 One screen, labels short, the defining structure visible at a glance.>
```

| 구성 요소 | 하는 일 | 위치 |
|---|---|---|
| <component> | <one line> | <path or §> |

## 피처와 타깃

| 모델 | 타깃 | 정의 | 위치 |
|---|---|---|---|
| <model> | <target column> | <how it is computed, in one line> | <path or §> |

| 피처 묶음 | 개수 | 예시 | 위치 |
|---|---|---|---|
| <group> | <n> | <two or three names> | <path or §> |

## 학습 방법

| 단계 | 방법 | 주요 설정 | 위치 |
|---|---|---|---|
| <split / model / loss / tuning / validation> | <one line> | <values as configured> | <path or §> |

## 주의사항

1. <the finding that most changes how this subject should be reused, with its location>
2. <a documented-vs-actual gap, a leakage risk, or something that could not be confirmed>

## 출처

| id | 유형 | 제목 | 링크·경로 | 읽은 깊이 |
|---|---|---|---|---|
| s01 | <paper / blog / repo / local> | <title> | <URL, arXiv id, repository path, or "<name>, 로컬 사본"> | <full / partial / abstract-only / failed> |
