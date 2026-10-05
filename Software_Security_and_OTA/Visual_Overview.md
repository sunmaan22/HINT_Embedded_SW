# Secure OTA Visual Overview

[문서 안내](./README.md) · [상세 개념](./Fundamentals.md) · [임베디드 SW 관점](./Embedded_SW_Study.md) · [실습](./lab/README.md)

## 1. 배포물 승인과 연결 상대 인증

```mermaid
flowchart LR
    SIGN["서명 주체<br/>개인키 보관"] -->|"manifest 서명"| DIST["배포 서버<br/>이미지 · manifest · 서명"]
    DIST -->|"TLS로 전달"| CLIENT["OTA Client"]
    TLS["사전 TLS Root<br/>예상 서버 이름"] --> CLIENT
    AUTH["사전 승인 서명자<br/>대상 · HW · 보안 하한"] --> CLIENT
    CLIENT --> VERIFY["서명 → 권한 → 정책<br/>청크 → 전체 이미지"]
    VERIFY -->|"통과"| WRITE["후보 슬롯 기록<br/>기록 후 재검사"]
    VERIFY -->|"실패"| STOP["설치 중단 · 사유 기록"]
```

TLS 신뢰와 펌웨어 서명 신뢰는 별도다. 단말은 배포물에 동봉된 Root·공개키를 무조건 승인하지 않는다.

## 2. A/B 설치와 실행 상태

```mermaid
flowchart TB
    A["확정 A<br/>보안 버전 5"] --> KEEP["쓰기 대상에서 제외"]
    NEW["승인 후보<br/>보안 버전 6"] --> B["비활성 B에 기록"]
    B --> HASH["저장된 B 재검사"]
    HASH -->|"불일치"| REC["A의 승인·하한 확인 후 복구"]
    HASH -->|"통과"| PENDING["candidate=B<br/>attempts=3 · floor=5"]
    PENDING --> TRY["횟수 감소·저장<br/>B 시험 부팅"]
    TRY --> HEALTH["필수 동작 점검"]
    HEALTH -->|"성공"| COMMIT["confirmed=B · floor=6<br/>논리적 확정 상태 갱신"]
    HEALTH -->|"실패 · 횟수 남음"| TRY
    HEALTH -->|"실패 · 소진"| REC
    REC -->|"허용 이미지 없음"| MODE["복구 모드"]
```

시험 중 B가 실행되어도 확정은 A다. floor를 조기에 6으로 높이면 A5 복구가 거부된다.

## 3. 수신 상태와 검증 기준

```mermaid
flowchart LR
    MAN["서명된 manifest<br/>청크 해시 · 전체 해시 · 크기"] --> AUTH["서명·권한 확인"]
    AUTH --> CHECK["저장 청크 재검증"]
    STATE["로컬 상태<br/>manifest ID · 수신 목록"] --> CHECK
    CHECK --> GOOD["0 · 1 · 3 · 4 재사용"]
    CHECK --> BAD["2 손상 / 5 · 6 · 7 미수신"]
    BAD --> RANGE["필요한 Range만 재요청"]
    GOOD --> JOIN["인덱스 순서대로 재조립"]
    RANGE --> JOIN
    JOIN --> FULL["길이·전체 해시 검사"]
```

수신 완료 목록이 인증된 해시를 대신하지 않는다. 모든 청크가 통과한 뒤에도 전체 이미지를 검사한다.

## 4. 보안 상태의 수명

```mermaid
flowchart TB
    NORMAL["일반 응용·네트워크"] -->|"권한과 인자 확인된 요청"| SECURE["보호된 보안 서비스"]
    SECURE --> TRUST["신뢰 집합 · epoch<br/>폐기 정보"]
    SECURE --> CONF["확정 슬롯 · 보안 하한"]
    NORMAL --> BOOT["부팅 후보 · 시도 횟수"]
    IMAGE["슬롯 A / B 이미지 복구"] -.->|"독립된 보안 상태를 되돌리지 않음"| TRUST
    RECKEY["독립 복구 승인권한"] -->|"운영 키 침해 후 승인"| SECURE
```

이 구조는 설계 책임을 표시한다. 파일 기반 코드가 실제 하드웨어 보안 경계를 구현한다는 의미는 아니다.

## 5. 다중 ECU 활성화 경로

```mermaid
flowchart LR
    START["A1/B3/C1<br/>허용된 출발"] -->|"B4 먼저"| MID["A1/B4/C1<br/>허용 중간 구성"]
    MID -->|"A2"| PART["A2/B4/C1<br/>허용 중간 구성"]
    PART -->|"C2 성공"| GOAL["A2/B4/C2<br/>목표 도달 · COMPLETE"]
    PART -->|"C2 실패"| FAIL["A2/B4/C1 유지<br/>ALLOWED · INCOMPLETE"]
    START -->|"A2 먼저"| REJECT["A2/B3/C1<br/>DEPENDENCY_REJECTED"]
```

패키지의 정품 여부, 실제 구성 허용 여부, 캠페인 완료 여부를 각각 기록한다.
