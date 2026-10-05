# Secure OTA Lab

강의의 해시·메시지 인증·서명·신뢰 전환·청크 재개·설치 복구·차량 구성을 **독립적인 Python 예제**로 재구성했다. PDF에 등장하는 원본 도구의 소스를 복제한 것이 아니며, 이 폴더의 CLI가 기준이다.

[문서 안내](../README.md) · [상세 개념](../Fundamentals.md) · [임베디드 SW 관점](../Embedded_SW_Study.md) · [구성도](../Visual_Overview.md)

## 1. 파일과 환경

| 파일 | 역할 |
|---|---|
| [otalab.py](./otalab.py) | 암호 실습·패키지 검증·청크 재개·A/B 기록·시험 부팅·신뢰 상태·차량 구성 |
| [tls_lab.py](./tls_lab.py) | RSA 인증서 fixture·제한된 PKI 검사·실제 로컬 TLS 1.3와 HTTP Range |
| [test_otalab.py](./test_otalab.py) | 성공/거부 경로·별도 프로세스 복구·네트워크 검사 |
| [requirements.txt](./requirements.txt) | Ed25519·X.509 연산용 `cryptography` |

- Python **3.10 이상**, TLS 1.3 지원 Python/OpenSSL 환경.
- 외부 OTA 서버·차량·CAN 장비는 필요 없다. TLS 실습은 `127.0.0.1`의 운영체제가 할당한 빈 포트만 사용한다.
- 파일 예제는 `--work`로 지정한 학습 디렉터리에 기록한다. 초기화·패키지 예제는 비어 있지 않은 폴더를 덮어쓰지 않는다. 각 독립 실험에는 새로운 경로를 사용한다.
- 실습에서 생성하는 개인키는 일회성 교육용 fixture다. 실제 개인키를 넣지 않는다. `publisher/`는 배포 주체의 모의 영역이며 단말이 발행자 개인키를 보관한다는 설계가 아니다.

```sh
cd Software_Security_and_OTA/lab
python -m venv .venv
# Windows PowerShell
.venv/Scripts/Activate.ps1
# Linux/macOS에서는: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest -v
```

## 2. 해시 · HMAC · 전자서명

```sh
python otalab.py hash
python otalab.py hash --attack
python otalab.py mac
python otalab.py sign
```

| 명령 | 관찰 |
|---|---|
| `hash` | 원본/변경 SHA-256 · 120비트 차이 · 기준 유지 시 비교 실패 |
| `hash --attack` | 기준값도 변경하면 비교 통과 · 충돌 공격 아님 |
| `mac` | 원본 True · 파일 변경/0 태그 False · 유출 키로 재생성한 태그 True |
| `sign` | 원본 PASS · 변경/다른 키는 SIGNATURE_INVALID · 동봉 키까지 교체하면 수학적 검사 PASS |

`sign`의 `replaced_key=PASS`는 취약한 비교 모델의 결과다. 안전한 패키지 경로는 뒤의 승인 목록 검사를 포함한다. 모든 공개키·서명은 실행 때 생성하므로 PDF의 출력 바이트와 같을 필요가 없다.

## 3. PKI · 실제 로컬 TLS · Range

```sh
python tls_lab.py pki
python tls_lab.py tls
```

| 사례 | 결과 |
|---|---|
| 신뢰 Root→Intermediate→codeSigning Leaf | `trusted_chain=PASS` |
| 만료된 Leaf | `CERT_EXPIRED` |
| serverAuth Leaf를 코드 서명용으로 사용 | `WRONG_USAGE` |
| 사전에 신뢰한 Root와 경로 끝이 다름 | `UNTRUSTED_ROOT` |
| TLS에서 SAN의 localhost를 확인 | `name_match=PASS`, `tls=TLSv1.3` |
| 동일 서버를 other.invalid로 검증 | `HOSTNAME_REJECTED` |
| 이미지 8청크를 HTTPS Range로 수신 | 요청 0~7 · 전체 해시 PASS |

`verify_fixed_chain`은 **이 코드가 생성한 RSA 3단 인증서만 검사하는 제한된 학습 함수**다. 일반 인증서 경로 구축, Name Constraints, 모든 Critical Extension, CRL/OCSP는 구현하지 않는다. 실제 TLS의 경로·이름 검증은 `ssl.create_default_context`의 Python/OpenSSL 검증에 맡기며, 인증서 확인을 끄지 않는다.

TLS 실행은 서버와 클라이언트를 같은 프로그램 안에서 띄우고 종료한다. 별도 인증서·키 파일은 임시 디렉터리에만 생성된다. 패키지 매니페스트 서명은 TLS 서버키와 별도 Ed25519 키로 검증한다.

## 4. 패키지와 단계별 거부

```sh
python otalab.py package --case normal
python otalab.py package --case bad_signature
python otalab.py package --case wrong_signer
python otalab.py package --case whitespace
python otalab.py package --case wrong_target
python otalab.py package --case wrong_hardware
python otalab.py package --case rollback
python otalab.py package --case tamper_after_join
```

| case | 조작 시점·내용 | 결과 |
|---|---|---|
| normal | 올바른 서명·권한·대상·HW·보안 버전 6 | 최종 이미지 PASS |
| bad_signature | 매니페스트 서명을 0으로 변경 | `SIGNATURE_INVALID` |
| wrong_signer | 비승인 키로 유효하게 서명 | `SIGNER_NOT_AUTHORIZED` |
| whitespace | 같은 JSON 값을 공백을 넣어 저장·원본 서명 유지 | `SIGNATURE_INVALID` |
| wrong_target | 승인 발행자가 다른 대상으로 재서명 | `TARGET_MISMATCH` |
| wrong_hardware | 승인 발행자가 rev1으로 재서명 | `HARDWARE_MISMATCH` |
| rollback | 보안 버전 5인 정상 서명 패키지 · 하한 6 | `SECURITY_VERSION_TOO_LOW` |
| tamper_after_join | 청크 검증 후 조립 이미지 1바이트 변경 | `PAYLOAD_HASH_REJECTED` |

거부 명령은 JSON 진단과 종료 코드 1을 반환한다. 정상 실험은 0이다. 설치/부팅 모의 결과의 `FAILED`·`FORBIDDEN`은 관측 결과로 정상 출력되므로 종료 코드 0일 수 있다. 자동 판정에서는 결과 필드도 확인한다.

`package`에 `--work`를 생략하면 임시 폴더를 사용한다. 파일을 남기려면 새 폴더를 지정한다.

## 5. 청크 재개

```sh
python otalab.py package --case chunk_corrupt --work work/resume_01
```

512 KiB 이미지를 64 KiB × 8로 나누고, 처음 다섯 청크를 저장한 상태에서 청크 2의 첫 바이트를 변경한다. 저장 상태에는 0~4가 완료로 남아 있지만 재검증 결과 2가 거부된다.

```text
requested = [2, 5, 6, 7]
image = PASS
```

이 명령은 **로컬 바이트 공급 함수로 재개 상태를 재현**한다. 실제 HTTPS Range는 `tls_lab.py tls`에서 별도로 실행한다. 청크를 재조립한 뒤 전체 해시도 검사한다.

| 남는 파일 | 확인 내용 |
|---|---|
| `manifest.json` | 검증 기준과 설치 조건 |
| `chunk_0.bin` ~ `chunk_7.bin` | 재사용·재수신 구간 |
| `download_state.json` | 매니페스트 ID와 로컬 완료 목록 |
| `firmware.bin` | 최종 재조립 결과 |

공통 `receive_chunks`는 호출 전에 서명·권한·스키마·정책 검증이 끝난 매니페스트를 받는 함수다. 임의로 파싱한 JSON을 곧바로 전달하지 않는다. `fetch_range`는 상태 206·Content-Range·Content-Length·읽기 길이를 검사하고 청크 크기보다 많은 데이터를 무제한 읽지 않는다.

## 6. 단일 영역과 A/B의 기록 중단 비교

각 명령을 별도 프로세스로 실행하여 영속 파일을 다시 읽는다.

```sh
python otalab.py init --work work/inplace_01
python otalab.py install --work work/inplace_01 --arch inplace --cut WRITING
python otalab.py boot --work work/inplace_01

python otalab.py init --work work/ab_cut_01
python otalab.py install --work work/ab_cut_01 --arch ab --cut WRITING
python otalab.py boot --work work/ab_cut_01
```

| 방식 | 쓰기 | old_preserved | 다음 boot |
|---|---|---|---|
| inplace | 확정 A의 앞 256 KiB 덮어쓰기 | False | 승인 해시 불일치 · booted_slot=null · 복구 모드 |
| ab | 비활성 B의 앞 256 KiB 덮어쓰기 | True | A의 이미지·정책 확인 후 booted_slot=A |

슬롯은 계속 512 KiB다. 파일 길이가 정상이어도 해시가 다르면 완성 이미지가 아니다. 중단 후보는 부팅 후보로 등록하지 않는다.

이 예제에서 inplace는 **부분 덮어쓰기 실패 비교용**이다. 정상 설치·시험·확정의 안내 경로는 A/B다. 파일의 정확한 반만 쓰고 동기화하는 실험으로 플래시의 실제 임의 전원 차단을 대신하지 않는다.

## 7. 정상 시험 부팅과 확정

```sh
python otalab.py init --work work/commit_01
python otalab.py install --work work/commit_01
python otalab.py boot --work work/commit_01 --health pass
python otalab.py boot --work work/commit_01
```

설치 직후 확정은 A, 후보는 B, 하한은 5다. 저장된 B를 다시 검증하고 부팅 횟수를 먼저 3→2로 저장한다. 모의 동작 확인 성공 후 `confirmed_slot=B`, `security_floor=6`을 한 파일의 논리적 기록으로 갱신하고 후보 정보를 정리한다. 다음 프로세스는 B를 확정 슬롯으로 선택한다.

`confirmed.json` 갱신 후 후보 정리 전에 중단되어도 재시작 시 같은 슬롯을 새 미확정 후보로 다시 시험하지 않도록 한다.

## 8. 부팅 실패와 조기 하한 상승

```sh
python otalab.py init --work work/health_fail_01
python otalab.py install --work work/health_fail_01
python otalab.py boot --work work/health_fail_01 --health fail
python otalab.py boot --work work/health_fail_01 --health fail
python otalab.py boot --work work/health_fail_01 --health fail
```

앞 두 실행의 `attempts_left`는 2, 1이다. 마지막 실행은 `update=FAILED`, `recovery=SUCCESS`, `booted_slot=A`이며 하한은 5로 유지한다.

```sh
python otalab.py init --work work/floor_fault_01
python otalab.py install --work work/floor_fault_01
python otalab.py inject-floor --work work/floor_fault_01 --value 6
python otalab.py boot --work work/floor_fault_01 --health fail
python otalab.py boot --work work/floor_fault_01 --health fail
python otalab.py boot --work work/floor_fault_01 --health fail
```

`inject-floor`는 잘못된 조기 상승을 재현하는 **고장 주입 명령**이며 정상 확정 API가 아니다. A의 버전 5가 하한 6 미만이므로 복구는 `RECOVERY_FORBIDDEN`, `booted_slot=null`, `mode=RECOVERY`다. 하한을 낮춰 우회하지 않는다.

## 9. 메타데이터 사본

후보 상태는 두 JSON 사본에 `magic`, `seq`, `candidate_slot`, `attempts_left`, `crc32`를 저장한다. 현재 사본을 보존하고 반대편을 갱신한다. 구조와 CRC를 통과한 최신 세대를 선택하며 같은 세대의 상충 기록은 거부한다.

자동 테스트는 최신 사본만 찢어진 경우 이전 유효 사본을 선택하고, 두 사본 모두 손상된 경우 `BOOT_METADATA_INVALID`를 확인한다. CRC는 우발 손상 검사다. 공격자도 다시 계산할 수 있으며 파일 기반 보호 저장소는 실제 보안 경계가 아니다.

## 10. 신뢰 상태와 침해 복구

```sh
python otalab.py trust
```

| 출력 | 해석 |
|---|---|
| epoch=2 · revoked_old_key=True | A 승인으로 B를 등록하고 A를 폐기 |
| replay=TRUST_STATE_ROLLBACK | 현재 상태와 다른 과거 세대 전이 거부 |
| compromised_operating_key=PASS | A가 탈취된 초기 상태에서는 공격자 전이도 A로 서명 가능 |
| independent_recovery_epoch=2 | 별도 복구키로 새 집합·폐기 정보를 승인 |

신뢰 상태는 메모리 딕셔너리로 모의한다. 실제 단조 증가 저장, 승인자 인증, X.509 경로·Root threshold 교체 프로토콜은 구현하지 않는다. 키 식별자는 이 예제에서 **32바이트 Ed25519 공개키의 64자리 hex**로 정의했다. PDF의 공개키 해시 ID 예제와 혼동하지 않는다.

## 11. 다중 ECU 구성과 캠페인

```sh
python otalab.py vehicle --initial 1/3/1 --goal 2/4/2
python otalab.py vehicle --initial 1/3/1 --goal 2/4/2 --fail-c
python otalab.py vehicle --goal 2/3/1
python otalab.py vehicle --goal 2/5/1
python otalab.py vehicle --order ABC
```

| 조건 | 결과 |
|---|---|
| B→A→C 정상 | actual=[2,4,2] · ALLOWED · COMPLETE · PASS |
| C 실패 | actual=[2,4,1] · ALLOWED · INCOMPLETE · BLOCKED |
| A2/B3/C1 목표 | DEPENDENCY_REJECTED |
| A2/B5/C1 목표 | CONFIG_NOT_APPROVED |
| A 먼저 활성화 | 중간 A2/B3/C1에서 DEPENDENCY_REJECTED |

이 명령은 승인 목록과 최소 의존 조건을 계산하는 구성 모델이다. 패키지별 암호 검증·ECU의 실제 기록·진단 전송·차량 전체 복구를 수행하지 않는다. 사전 경로와 실제 최종 구성을 따로 출력한다.

## 12. 검증 결과와 한계

`python -m unittest -v`로 다음을 확인한다.

작성 시 검증 환경은 Python 3.12.14 · cryptography 50.0.1이며, **12개 테스트 메서드와 그 안의 부정 시험이 모두 통과**했다.

- 인증 성공·위조 모델·서명/권한/대상/HW/구버전 거부와 원본 바이트 검증.
- 중복 JSON 키·bool 타입·크기 상한·청크 수·짧은 마지막 청크 검사.
- 손상/미수신 청크 재요청과 재개 매니페스트 ID 불일치 거부.
- **별도 Python 프로세스**의 boot에서 단일 영역 실패와 A/B 보존을 비교.
- 후보 횟수 영속화·Health 실패 복구·확정 때 하한 상승·조기 상승 복구 거부.
- 메타데이터 사본 손상·세대 충돌·잘못된 구조 검사.
- 신뢰 세대 후퇴·폐기 키 재등록·복구권한 분리·다중 ECU 경로 판정.
- 실제 로컬 TLS 1.3의 이름 불일치와 HTTPS Range 수신·잘못된 Range 응답 거부.

검증 범위는 **교육용 코드의 논리와 로컬 파일·TLS 동작**이다. HSM/TEE/eFuse/RPMB의 보호, 실제 MCU 부팅, 플래시 손상 모델, 서비스/워치독/차량 상태, Uptane 전체 검증과 표준 적합성은 검증하지 않았다.
