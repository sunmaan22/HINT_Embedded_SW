/*
 * FreeRTOSConfig.h
 *
 * Created: 2026-09-16 오후 11:21:15
 *  Author: IncheolShin
 */

#ifndef FREERTOS_CONFIG_H
#define FREERTOS_CONFIG_H

#include <avr/io.h>

// MCU 클럭 설정 (심볼을 사용하거나 직접 지정)
#ifndef F_CPU
#define F_CPU 14745600UL
#endif
#define configCPU_CLOCK_HZ          ( ( uint32_t ) F_CPU )

// 기본 커널 설정
#define configUSE_IDLE_HOOK         0   // 0으로 설정 (사용 안 함)
#define configUSE_TICK_HOOK         0   // 0으로 설정 (사용 안 함)
#define configUSE_PREEMPTION        1   // 선점형 스케줄링 사용
#define configTICK_RATE_HZ          ( ( TickType_t ) 1000 ) // 1ms 단위 틱

// 메모리 설정 (ATmega128은 SRAM이 4KB로 매우 작으므로 최적화가 필수입니다)
#define configMINIMAL_STACK_SIZE    ( ( uint16_t ) 85 )     // 각 태스크의 최소 스택 크기 (바이트 단위)
#define configTOTAL_HEAP_SIZE       ( ( size_t ) 1500 )     // FreeRTOS 커널이 사용할 총 힙 크기

// 태스크 설정
#define configMAX_PRIORITIES        4   // 우선순위 개수 (0 ~ 3)
#define configMAX_TASK_NAME_LEN     8   // 태스크 이름 최대 길이

// 타이머 및 기타 기능 정의
#define configUSE_16_BIT_TICKS      1   // 8비트/16비트 MCU이므로 1로 설정하여 메모리 절약
#define configIDLE_SHOULD_YIELD     1

// 사용할 API 활성화 (1: 활성화, 0: 비활성화)
#define INCLUDE_vTaskPrioritySet        1
#define INCLUDE_uxTaskPriorityGet       1
#define INCLUDE_vTaskDelete             1
#define INCLUDE_vTaskCleanUpResources   0
#define INCLUDE_vTaskSuspend            1
#define INCLUDE_vTaskDelayUntil         1
#define INCLUDE_vTaskDelay              1

#endif /* FREERTOS_CONFIG_H */