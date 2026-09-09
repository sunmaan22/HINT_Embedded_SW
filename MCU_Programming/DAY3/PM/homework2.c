/*
 * homework2.c
 *
 * 3일차 오후 통합 프로젝트 — Auto Light ECU
 *
 *  3일차 오후 : 드라이버 스택 + 상태 기계 조립
 *  보드       : SDK ATMEGA128A 2020
 *      입력  CDS = ADC1(PF1) · SW2 = PE4(INT4)
 *      시간  Timer0 CTC 10 ms tick
 *      출력  PWM = OC3A(PE3, D9) · LED = PORTB · UART1(USB)
 *
 *  요구사항
 *    · AUTO : 어두워지면 D9 를 밝게, 밝아지면 끈다
 *    · ON   : 조도와 무관하게 항상 100 %
 *    · SW2 로 두 상태를 전환한다
 *    · 경계 조도에서 깜빡이지 않도록 히스테리시스를 쓴다
 *
 *  구조
 *    ISR  : 이벤트 플래그만 설정한다 (버튼 · 타이머 · ADC)
 *    main : 이벤트를 모아 상태를 갱신하고 출력을 만든다
 *    블로킹 delay 가 한 곳도 없다
 */
#define F_CPU 14745600UL

#include <avr/interrupt.h>
#include <stdint.h>

#include "led.h"
#include "btn.h"
#include "timer.h"
#include "adc.h"
#include "pwm.h"
#include "uart.h"

typedef enum {
    ST_AUTO = 0,
    ST_ON
} state_t;

/* 조도 임계값 — 히스테리시스 (경계에서 떨리는 것을 막는다)
   실습실 조명에 따라 달라지므로 실습 1 의 로그로 raw 값을 먼저 확인하고 정한다 */
#define DARK_ENTER   380        /* 이보다 어두워지면 "어둡다" 로 */
#define DARK_EXIT    460        /* 이보다 밝아져야 "밝다" 로 되돌아온다 */

int main(void)
{
    state_t  state = ST_AUTO;
    uint8_t  bev, tev, aev;
    uint16_t val[2] = {0, 0};
    uint8_t  dark = 0;
    uint8_t  duty = 0;

    led_init();
    btn_init();
    btn_int_enable();
    timer_init();
    adc_init();
    pwm_init();
    uart_init();

    sei();                          /* 여기서 딱 한 번 */
    uart_puts("\n=== Auto Light ECU  (SDK ATmega128A) ===\n");

    while (1) {
        /* ---------- ① 이벤트 수집 ---------- */
        bev = btn_get_events();
        tev = timer_get_events();

        if (tev & TIMER_EVENT_50MS)
            adc_start(ADC_CH_CDS);              /* 20 Hz */

        aev = adc_get_event(val);

        /* ---------- ② 상태 전이 ---------- */
        if (bev & BTN_EVENT_SW2)
            state = (state == ST_AUTO) ? ST_ON : ST_AUTO;

        /* ---------- ③ 출력 계산 ---------- */
        if (aev & ADC_EVENT_CDS) {              /* 히스테리시스 */
            if (!dark && val[ADC_CH_CDS] < DARK_ENTER)  dark = 1;
            if ( dark && val[ADC_CH_CDS] > DARK_EXIT)   dark = 0;
        }

        duty = (state == ST_ON) ? 100 : (dark ? 80 : 0);
        pwm_set_duty(duty);
        led_write(dark ? 0x0F : 0x00);          /* 어두우면 절반 점등 */

        /* ---------- ④ 표시 ---------- */
        if (tev & TIMER_EVENT_1S) {
            uart_puts(state == ST_ON ? "ON   " : "AUTO ");
            uart_puts("cds=");     uart_put_uint16(val[ADC_CH_CDS]);
            uart_puts(dark ? "  dark" : "  bright");
            uart_puts("  duty=");  uart_put_uint16(duty);
            uart_puts("%\n");
        }
    }
}

/*
 *  검증 항목
 *   1) 센서를 가리면 D9 가 밝아지고 손을 떼면 어두워지는가
 *   2) 경계 조도에서 깜빡거리지 않는가 (히스테리시스가 듣는가)
 *   3) SW2 로 ON 으로 바꾸면 조도와 무관하게 100 % 인가
 *   4) 블로킹 delay 가 한 곳도 남아 있지 않은가
 *   5) ISR 은 전부 플래그만 설정하고 끝나는가
 *   6) main 에 PORTB / ADMUX 같은 레지스터 이름이 남아 있지 않은가
 *
 *  더 해 볼 것
 *   · DARK_ENTER / DARK_EXIT 를 같은 값으로 만들어 깜빡임을 직접 확인한다
 *   · TEXT LCD(clcd.c) 를 붙여 상태를 화면에 표시한다
 *   · 가변저항 VR3(ADC0) 로 밝기를 직접 정하는 MANUAL 상태를 추가한다
 */
