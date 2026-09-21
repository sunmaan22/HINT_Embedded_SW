/*
 * LED_DEMO.c
 *
 * Created: 2026-09-16 오후 10:36:15
 * Author : IncheolShin
 */

#define F_CPU 14745600UL
#include <avr/io.h>
#include "FreeRTOS.h"
#include "task.h"

// LED를 제어하는 간단한 태스크
void vLEDBlinkTask(void *pvParameters) {
    // PORTB 전체를 출력으로 설정
    DDRB = 0xFF;
    PORTB = 0x00;
    for( ;; ) {
        PORTB ^= 0xFF; // 모든 LED 상태 반전

        // configTICK_RATE_HZ가 1000이므로 1000 ticks = 1초입니다.
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

int main(void) {
    // 1. 태스크 생성 (최소 스택 크기 사용, 우선순위 1)
    xTaskCreate(vLEDBlinkTask, "LED_TSK", configMINIMAL_STACK_SIZE, NULL, 1, NULL);

    // 2. 스케줄러 시작 (이 함수가 호출되면 태스크 구동이 시작됩니다)
    vTaskStartScheduler();

    // 메모리 부족 등의 이유로 스케줄러 실행에 실패하면 아래로 내려옵니다.
    while (1) {
        // 에러 표시용 루프
    }
}