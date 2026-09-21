# RTOS Programming (FreeRTOS on ATmega128A)

RTOS의 기본 개념부터 FreeRTOS의 구조, 그리고 ATmega128A 보드 위에서 LED·LCD를 FreeRTOS 태스크로 제어하는 실습까지 정리한 기술 노트이다. 강의자료(개념)와 실제로 빌드·구동까지 완료한 실습 코드([RTOS_LED_Demo](./RTOS_LED_Demo/), [RTOS_LCD_LED_CTRL](./RTOS_LCD_LED_CTRL/))를 함께 다룬다.

## 1. 과정 개요

| 구분 | 내용 |
|---|---|
| 강의 | K 뉴딜아카데미 부산 · 현대자동차 임베디드 AI 과정, RTOS 프로그래밍 SW 트랙 |
| 강의자 | 신인철 |
| 대상 보드 | SDK ATMEGA128A |
| 기본 환경 | C, AVR-GCC, Microchip Studio, ISP, FreeRTOS-Kernel |
| 학습 목표 | RTOS/멀티태스킹 개념 이해 → FreeRTOS 커널 구조 파악 → 순수 레지스터 제어(Bare-metal) LED·LCD 데모 → FreeRTOS 태스크 기반 LED·LCD 데모 → 두 태스크를 하나의 스케줄러에 통합 |

### 강의 구성

| 자료 | 핵심 내용 |
|---|---|
| 0장. RTOS 기본 개념 | Multiprogramming·Time-sharing·Real-Time OS의 정의, Task와 Context Switching, Kernel과 Scheduler, Preemptive/Non-Preemptive Kernel, Critical Section과 Mutual Exclusion, Semaphore, Deadlock, Priority Inversion, Task Communication/Synchronization, Interrupt Service, Reentrancy |
| 1장. FreeRTOS 개요 | FreeRTOS의 역사(Richard Barry, 2003 / AWS, 2016), Hard/Soft Real-Time, Task 단위 실행, RTOS를 쓰는 이유(타이밍 추상화, 유지보수성, 모듈화, 팀 개발, 테스트 용이성, 코드 재사용, Event-Driven 효율, Idle Task/전력 관리, 유연한 인터럽트 처리), FreeRTOS 커널이 제공하는 기능 목록 |
| 2장. FreeRTOS 포트 구조 | `Kernel + Port` 구성, `FreeRTOSConfig.h`의 역할, `FreeRTOS/Source`의 파일 구성, `portable/[compiler]/[architecture]`와 Heap 옵션, Demo Project 구성과 `main()` 골격, `TickType_t`/`BaseType_t`, 변수·함수 명명 규칙(prefix) |
| 1. LCD Demo | Bare-metal LCD_DEMO 프로젝트 생성과 `lcd.h`/`lcd.c` 드라이버 작성, 빌드, ISP 프로그래밍 |
| 2. LED Demo | Bare-metal LED_DEMO 프로젝트 생성, `F_CPU` 설정, 빌드, ISP 프로그래밍 |
| 3. RTOS_LED Demo | FreeRTOS-Kernel 소스를 프로젝트에 포함하고 LED 태스크로 재작성 → [RTOS_LED_Demo](./RTOS_LED_Demo/) |
| 4. RTOS_LCD Demo | RTOS_LED_DEMO 구조에 `lcd.c`/`lcd.h`를 결합해 FreeRTOS 태스크로 LCD 출력 |
| 5. RTOS_LCD_LED 제어 실습 | LCD·LED 두 태스크를 하나의 스케줄러에서 함께 구동하는 통합 실습 → [RTOS_LCD_LED_CTRL](./RTOS_LCD_LED_CTRL/) |

## 2. RTOS 기본 개념

### Multitasking과 Context Switching

여러 작업(Task)을 짧은 시간 단위로 번갈아 실행해 동시에 실행되는 것처럼 보이게 하는 방식이 멀티태스킹이다. Task를 전환할 때 커널은 현재 Task의 레지스터·스택 포인터 등 실행 문맥을 저장하고, 다음 Task의 문맥을 복원한다. 이 과정이 **Context Switching**이며, 각 Task는 자신만의 스택에 이 정보를 보존한다.

### Kernel과 Scheduler

Kernel은 Context Switching, Task Scheduling, Memory Management 등 멀티태스킹 OS의 핵심 기능을 제공하는 부분이다. 여러 Task 중 어떤 Task를 실행할지 결정하는 부분이 **Scheduler**(Dispatcher)이며, 대부분의 RTOS는 우선순위 기반 스케줄링(Priority-based Scheduling)을 사용한다. 같은 우선순위 안에서는 FIFO 또는 Round-Robin으로 처리한다.

### Preemptive vs Non-Preemptive Kernel

| 구분 | 동작 | 특징 |
|---|---|---|
| Non-Preemptive | 실행 중인 Task가 스스로 커널에 제어권을 넘길 때만 전환 | Cooperative Multitasking. 인터럽트 지연(latency)은 짧지만 우선순위가 높은 Task가 즉시 실행되지 않을 수 있다 |
| Preemptive | 우선순위가 더 높은 Task가 Ready 상태가 되면 즉시 선점 | 응답성이 높아 실시간 시스템에 적합. FreeRTOS 기본값(`configUSE_PREEMPTION = 1`) |

### Critical Section과 동기화 도구

- **Critical Section / Mutual Exclusion** — 여러 Task가 공유 자원(Shared Memory 등)에 동시에 접근하지 못하도록 보호하는 구간과 그 원칙. 짧은 구간은 인터럽트를 비활성화하는 방식으로, 더 일반적으로는 세마포어로 보호한다.
- **Semaphore** — Dijkstra가 고안한 동기화 메커니즘. 카운트가 0/1인 **Binary Semaphore**와 여러 개인 **Counting Semaphore**로 나뉘며, 자원 보호(Mutual Exclusion)와 Task 간 동기화(Synchronization) 양쪽에 쓰인다.
- **Deadlock** — 여러 Task가 서로가 점유한 자원을 기다리며 무한히 대기하는 상태(Dijkstra의 "식사하는 철학자" 문제로 설명).
- **Priority Inversion** — 낮은 우선순위 Task가 세마포어를 점유한 사이, 중간 우선순위 Task가 선점하여 결과적으로 높은 우선순위 Task가 대기하게 되는 현상.

### Task 통신과 동기화, 인터럽트

- **Task Communication**: 전역 변수 공유(접근 보호 필요) 또는 Message Passing(Mailbox·Queue·Pipe).
- **Task Synchronization**: 세마포어, Event Flag(Event Group), Signal로 처리한다.
- **Interrupt Service**: 인터럽트는 비동기 이벤트로 CPU를 즉시 호출한다. ISR은 최대한 짧게 유지하고, 긴 처리는 별도 Task(HISR, FreeRTOS의 Deferred/Daemon Task)로 넘긴다.
- **Reentrancy**: 여러 Task가 동시에 호출해도 안전한 코드를 Reentrant Code라 하며, 공유 자원을 다룰 때는 상호 배제가 필요하다.

## 3. FreeRTOS 개요

### 역사와 Hard/Soft Real-Time

FreeRTOS는 Richard Barry가 2003년 공개한 오픈소스 실시간 커널이며, 2016년부터 Amazon Web Services(AWS)가 관리한다. MIT 라이선스로 배포된다.

| 구분 | 의미 |
|---|---|
| Soft Real-Time | 데드라인을 놓쳐도 시스템 전체 성능이 서서히 저하될 뿐 치명적이지 않다 |
| Hard Real-Time | 데드라인을 반드시 지켜야 한다. 에어백처럼 지연 자체가 곧 치명적 실패로 이어진다 |

FreeRTOS는 Task 단위 실행과 우선순위 기반의 Preemptive Scheduler로 이 두 요구를 함께 만족시키도록 설계되었다.

### RTOS를 쓰는 이유

| 항목 | 설명 |
|---|---|
| 타이밍 추상화 | 응용 코드가 RTOS API만 호출하면 되고, 실제 스케줄링·타이밍은 커널이 담당한다 |
| 유지보수성·확장성 | 새 기능을 새로운 Task로 추가하기 쉽다 |
| 모듈화 | 기능별로 Task를 분리해 설계·디버깅 단위를 명확히 한다 |
| 팀 개발·테스트 용이성 | Task 단위로 독립 개발·개별 테스트가 가능하다 |
| 코드 재사용 | 잘 분리된 Task/드라이버는 다른 프로젝트에도 재사용된다 |
| 효율(Event-Driven) | `while(1)` Polling 대신 이벤트 발생 시에만 깨어나 CPU 낭비를 줄인다 |
| 전력 관리 | Idle Task와 Tick-less Mode로 유휴 구간에 CPU를 저전력 모드로 전환한다 |
| 유연한 인터럽트 처리 | ISR은 최소한만 처리하고 나머지는 Deferred/Daemon(Timer) Task로 넘겨 Task 우선순위 체계 안에서 처리한다 |

### FreeRTOS Kernel이 제공하는 기능

Preemptive/Cooperative Scheduling, Time Slicing, Task Priority, Task Notification, Queue, Binary/Counting Semaphore, Mutex, Recursive Mutex, Software Timer, Event Group.

## 4. FreeRTOS 포트 구조

FreeRTOS는 **Bare-metal 위에서 동작하는 커널 + 하드웨어별 Port**로 구성된다. 커널 자체는 순수 C로 작성되어 있고, 컴파일러·아키텍처 조합마다 별도의 Port 레이어가 필요하다.

```
FreeRTOS/Source/
├── tasks.c            Task 생성·스케줄링 핵심
├── list.c             Task 리스트 자료구조 (tasks.c가 사용)
├── queue.c            Queue, Semaphore, Mutex
├── timers.c           Software Timer
├── event_groups.c     Event Group
├── stream_buffer.c    Stream/Message Buffer
├── croutine.c         Co-routine (레거시, 8비트 MCU용 경량 기능)
├── include/           공개 API 헤더 (task.h, queue.h, semphr.h, timers.h, ...)
└── portable/
    ├── MemMang/            heap_1.c ~ heap_5.c (동적 메모리 전략 선택)
    └── [compiler]/[architecture]/   컴파일러·아키텍처별 Port (예: GCC/ATMega323)
```

- `FreeRTOSConfig.h`는 프로젝트별 커널 동작(선점 여부, Tick 주기, 힙 크기, 우선순위 개수, 사용할 API 등)을 정의한다. **반드시 `FreeRTOS.h`보다 먼저 include되는 위치**(Include Path)에 있어야 한다.
- `configSUPPORT_DYNAMIC_ALLOCATION`이 0이 아니면 `portable/MemMang`의 heap 구현 중 하나를 선택해 포함해야 한다. 이 실습은 가장 단순한 `heap_1.c`(할당만 하고 해제는 하지 않는 방식)를 사용한다.
- Include Path는 ① `FreeRTOS/Source/include`, ② Port 경로 `FreeRTOS/Source/portable/[compiler]/[architecture]`, ③ `FreeRTOSConfig.h`가 있는 경로 세 곳을 모두 등록해야 한다.
- `main()`은 하드웨어 초기화 → 응용 Task 생성 → `vTaskStartScheduler()` 호출 순으로 구성되며, 스케줄러 진입 이후의 `for(;;)`는 힙 부족 등으로 스케줄러 시작에 실패했을 때만 도달한다.

### 타입과 명명 규칙

| 타입 | 의미 |
|---|---|
| `TickType_t` | Tick Interrupt 발생 횟수를 저장하는 타입. `configTICK_TYPE_WIDTH_IN_BITS`(또는 `configUSE_16_BIT_TICKS`)로 16/32/64비트를 선택한다 |
| `BaseType_t` | 아키텍처에 가장 효율적인 정수 타입. 함수 반환값이나 `pdTRUE`/`pdFALSE` 같은 Boolean 표현에 쓰인다 |

| Prefix | 의미 | 예 |
|---|---|---|
| `v` | 반환 타입 `void` | `vTaskPrioritySet()` |
| `x` | `BaseType_t` 또는 구조체(Task/Queue Handle 등) | `xQueueReceive()` |
| `p` / `pv` | 포인터 | `pvTimerGetTimerID()` |
| `u` | unsigned | `ucValue` |
| `c` | `char` | `pcString`의 문자 |
| `prv` | 파일 내부 전용(Private) 함수 | `prvSetupHardware()` |
| `config` | `FreeRTOSConfig.h`의 설정값 | `configUSE_PREEMPTION` |
| `pd` / `err` | `projdefs.h`의 상수 | `pdTRUE`, `errQUEUE_FULL` |

## 5. 실습 진행 순서

Microchip Studio(GCC C Executable Project)에서 아래 순서로 프로젝트를 단계적으로 확장한다. 각 단계는 이전 단계의 코드를 그대로 이어받아 FreeRTOS 요소를 더하는 방식으로 진행된다.

| 단계 | 프로젝트 | 방식 | 내용 | 저장소 코드 |
|---|---|---|---|---|
| 1 | LCD_DEMO | Bare-metal | `lcd.h`/`lcd.c`로 문자 LCD(HD44780 호환) 드라이버 작성 후 직접 호출 | 강의자료만(코드 미보관) |
| 2 | LED_DEMO | Bare-metal | `F_CPU` 매크로 설정 후 `main()`에서 직접 PORTB 제어 | 강의자료만(코드 미보관) |
| 3 | RTOS_LED_DEMO | FreeRTOS | FreeRTOS-Kernel(`heap_1.c`, `list.c`, `queue.c`, `tasks.c`, Port `port.c`)을 프로젝트에 포함하고, LED 제어를 `vLEDBlinkTask` Task로 재작성 | [RTOS_LED_Demo](./RTOS_LED_Demo/) |
| 4 | RTOS_LCD_DEMO | FreeRTOS | RTOS_LED_DEMO 구조에 `LCD_DEMO`의 `lcd.c`/`lcd.h`를 결합해 LCD 출력을 Task로 재작성 | 강의자료만(코드 미보관) |
| 5 | RTOS_LCD_LED_CTRL | FreeRTOS | RTOS_LCD_DEMO의 `Source` 구성을 그대로 이어받아 `vLEDBlinkTask`와 `vLCDPrintTask` **두 Task를 동시에 생성**하는 통합 프로젝트 | [RTOS_LCD_LED_CTRL](./RTOS_LCD_LED_CTRL/) |

공통 프로젝트 생성 절차: Microchip Studio → `GCC C Executable Project` → Device로 `ATmega128` 선택 → FreeRTOS-Kernel(공식 저장소 `git clone https://github.com/FreeRTOS/FreeRTOS-Kernel.git`)의 `list.c`/`queue.c`/`tasks.c`/`timers.c`/`event_groups.c`와 `portable/MemMang/heap_1.c`, `portable/GCC/ATMega323/port.c`를 프로젝트에 추가 → `FreeRTOSConfig.h` 작성 → Include Path 3곳 등록 → 빌드 → AVRISP 등으로 Device Programming.

> 이 저장소에는 FreeRTOS 커널 자체(라이브러리 소스)는 포함하지 않고, 실습에서 직접 작성한 `main.c`·`FreeRTOSConfig.h`·`lcd.c`/`lcd.h`만 보관한다. 전체 프로젝트(커널 포함, `.atsln`)는 로컬의 `RTOS_LED_DEMO`, `RTOS_LCD_LED_CTRL` 폴더에 있다.

## 6. 완성 코드 정리

### [RTOS_LED_Demo](./RTOS_LED_Demo/) — LED 1개 Task

```c
void vLEDBlinkTask(void *pvParameters) {
    DDRB = 0xFF; PORTB = 0x00;
    for( ;; ) {
        PORTB ^= 0xFF;                    // PORTB 전체 LED 토글
        vTaskDelay(pdMS_TO_TICKS(500));   // 500 ms 대기 (Blocking, 다른 Task 실행 가능)
    }
}
```

`xTaskCreate(vLEDBlinkTask, "LED_TSK", configMINIMAL_STACK_SIZE, NULL, 1, NULL)`로 우선순위 1의 Task 하나만 생성하고 `vTaskStartScheduler()`로 구동한다.

### [RTOS_LCD_LED_CTRL](./RTOS_LCD_LED_CTRL/) — LED + LCD 2개 Task

```c
void vLEDBlinkTask(void *pvParameters) { /* 위와 동일 */ }

void vLCDPrintTask(void *pvParameters) {
    lcd_init();
    while (1) {
        lcd_gotoxy(0, 0); lcd_string("ATmega128");
        lcd_gotoxy(0, 1); lcd_string("Hello LCD!");
        _delay_ms(500);
        lcd_clear();
        _delay_ms(500);
    }
}

int main(void) {
    xTaskCreate(vLEDBlinkTask, "LED_TSK", configMINIMAL_STACK_SIZE, NULL, 1, NULL);
    xTaskCreate(vLCDPrintTask, "LCD_TSK", configMINIMAL_STACK_SIZE, NULL, 1, NULL);
    vTaskStartScheduler();
    while (1) { /* 스케줄러 시작 실패 시에만 도달 */ }
}
```

두 Task 모두 우선순위 1로 동일하다. `vLCDPrintTask`는 `_delay_ms()`(Blocking Busy-wait)를 쓰는 반면 `vLEDBlinkTask`는 `vTaskDelay()`(Task를 Blocked 상태로 전환)를 쓴다는 점이 다르다 — 전자는 대기 중 CPU를 점유하지만, 같은 우선순위에서 Time Slicing이 동작하면 다른 Task도 번갈아 실행된다. 완전히 협조적으로 CPU를 양보하려면 `_delay_ms()` 대신 `vTaskDelay()`로 통일하는 편이 더 바람직하다.

### FreeRTOSConfig.h 주요 설정값

| 매크로 | 값 | 의미 |
|---|---|---|
| `configCPU_CLOCK_HZ` | `F_CPU` (14,745,600) | 보드 클럭 |
| `configUSE_PREEMPTION` | 1 | 선점형 스케줄링 사용 |
| `configTICK_RATE_HZ` | 1000 | Tick 주기 1 ms (1000 tick = 1초) |
| `configMINIMAL_STACK_SIZE` | 85 | Task별 최소 스택(바이트) — ATmega128 SRAM 4 KB에 맞춰 최소화 |
| `configTOTAL_HEAP_SIZE` | 1500 | 커널이 `heap_1.c`로 관리하는 총 힙 크기 |
| `configMAX_PRIORITIES` | 4 | 우선순위 단계 수(0~3) |
| `configUSE_16_BIT_TICKS` | 1 | 8/16비트 MCU이므로 16비트 Tick 카운터로 메모리 절약 |

### LCD 핀 연결과 드라이버 구조

`lcd.h`가 정의하는 제어 핀은 `RS = PG0`, `RW = PG1`, `E = PG2`이며, 데이터 버스는 `PORTA`를 사용한다(문자 LCD는 8비트 병렬 인터페이스, HD44780 호환 명령 체계). `lcd.c`는 Busy Flag 폴링(`lcd_busy()`)으로 LCD의 처리 완료를 확인한 뒤 다음 명령·데이터를 전송하는 구조이며, `lcd_init/lcd_command/lcd_data/lcd_clear/lcd_gotoxy/lcd_string`을 응용 코드(Task)에 API로 제공해 레지스터 제어를 감춘다 — [MCU_Programming](../MCU_Programming/)에서 정리한 드라이버 계층 분리 원칙과 같은 방식이다.

## 7. 빌드와 프로그래밍

1. Microchip Studio에서 해당 폴더의 `.atsln`을 연다(이 저장소에는 소스만 있으므로 로컬 원본 프로젝트 또는 새 GCC C Executable Project에 이 파일들을 복사해 사용한다).
2. 프로젝트 속성에 `F_CPU=14745600UL`을 정의하고, Include Path에 FreeRTOS `Source/include`, Port 경로, `FreeRTOSConfig.h` 경로를 등록한다.
3. `Build Solution`으로 `.hex`를 생성한다.
4. AVRISP 등 ISP 프로그래머로 Device Programming을 수행해 ATmega128A 보드에 다운로드한다.

## 8. 다음 학습 방향

- `vLCDPrintTask`의 `_delay_ms()`를 `vTaskDelay()`로 교체해 완전한 협조적 스케줄링으로 정리하기.
- 두 Task 사이에 공유 자원(LCD)이 생기는 3번째 Task(예: 버튼 입력)를 추가할 때 Queue 또는 Semaphore로 Task Communication/Synchronization 적용해 보기.
- [MCU_Programming](../MCU_Programming/)의 인터럽트·타이머·ADC 드라이버를 FreeRTOS Task/Queue로 옮겨 Bare-metal Super Loop 설계와 RTOS 기반 설계를 비교하기.
