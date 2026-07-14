# 🎯 VIP DAU 개선 플랜 트래커

VIP DAU 개선 플랜의 **플랜 → 실행 → 실적**을 추적하는 Streamlit 대시보드입니다.
진단(도달·이탈 대시보드)이 '왜'를 설명한다면, 여기는 '무엇을 언제 했고 효과가 났는가'를 봅니다.

## 구성

| 섹션 | 내용 |
|---|---|
| ① 플랜 | 목표 시나리오(보수 −8% / 기본 −5% / 상한 −2.5%) + 레버 3단(트랙 B 즉시 / 트랙 A 단기 / 상시) |
| ② 실행 현황 | `data/actions.csv` 과제 체크리스트 — 앱에서 편집 후 CSV 다운로드 → 레포 교체 시 영구 반영 |
| ③ 실적 — DAU | 월별 VIP DAU를 전년 동월·시나리오 밴드에 겹쳐 추적 (완료월 기준, 부분월 자동 제외) |
| ④ 실적 — 트랙 B | 재설치 캠페인: 재설치율·재방문·대조군 리프트·비용 효율 자동 집계 |
| ⑤ 실적 — 트랙 A | 실시간 vs D-1 A/B: 재방문율 리프트 + 두 비율 z-검정 자동 판정 |
| ⑥ 판정 기준 | 트랙별 성공/실패 정의 + 결과 업로드 CSV 템플릿 다운로드 |

## 데이터

- **업로드형** (레포에 커밋하지 않음 — 공개 레포 민감정보 방지):
  - 채널별 일 DAU (.xlsx, B2B 제외) — DAU 실적 트래킹 (권장)
  - 월별 VIP MAU/DAU (.xlsx, 간이 포맷) — 채널 파일 없을 때 대체
  - 트랙 B 결과 (.csv): `date, group(발송/대조), targets, reinstalls, revisits_7d, optouts, cost`
  - 트랙 A 결과 (.csv): `date, group(실시간/D-1), sent, clicks, revisits_d1`
- **레포 저장**: `data/actions.csv` (실행 과제 상태)만

## 실행 / 배포

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit Cloud: 레포 연결 → Main file `app.py` → Deploy
