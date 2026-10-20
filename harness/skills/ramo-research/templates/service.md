---
type: Research Topic
title: "<서비스 이름> 운영 구조"
kind: service
summary: <one line for the overview table: what the service provides and its defining policy or flow>
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
  - 서비스 하나의 시스템 흐름, 운영 정책, 변경 이력을 처음 보는 사람이 10분 안에 잡게 쓰는 문서임
  - 문장보다 그림과 표. 절마다 표 하나나 다이어그램 하나가 중심이고 글은 그 앞뒤 2-3문장
  - 주장마다 위치를 붙임. 표는 `위치` 열, 문장은 끝 괄호 (문서: 소제목, 코드: 경로 또는 file::symbol)
  - 정책은 무엇을 하는지와 언제 적용되는지를 함께 적음. 수치(상·하한, 비율)는 단위와 조건과 함께
  - 문서가 다루지 않는 절은 지우지 말고 "해당 없음 — 사유" 한 줄. 추정으로 채우지 않음
  - 비공개 문서는 요약함. 직접 인용은 2문장 이하, 자격 증명·호스트·개인정보는 옮기지 않음
  - `##` 만 씀. 문서 기준선 약 150행
-->

# <서비스 이름> 운영 구조

<2-3 sentences: what the service provides to whom, and the one policy or flow a reader must remember.> (s01)

## 전체 흐름

```text
<a box-and-arrow diagram of the request or data flow: caller → service → dependencies → output.
 One screen, labels short.>
```

| 구성 요소 | 하는 일 | 위치 |
|---|---|---|
| <system or step> | <one line> | <heading or path> |

## 운영 정책

| 정책 | 내용 | 적용 조건 | 위치 |
|---|---|---|---|
| <policy name> | <what it does, with values and units> | <when it applies> | <heading> |

## 변경 이력

| 시점 | 변경 | 이유 | 위치 |
|---|---|---|---|
| <YYYY-MM or as stated> | <what changed> | <why, as the source states it> | <heading> |

## 주의사항

1. <a contradiction, a stale statement, a policy whose condition is unclear, or something that could not be confirmed>
2. (해석) <what would not transfer to our service and why>

## 출처

| id | 유형 | 제목 | 링크·경로 | 읽은 깊이 |
|---|---|---|---|---|
| s01 | <blog / repo / local> | <title> | <URL, repository path, or "<name>, 로컬 사본"> | <full / partial / abstract-only / failed> |
