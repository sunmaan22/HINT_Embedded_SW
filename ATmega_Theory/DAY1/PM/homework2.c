/*
 * homework2.c
 *
 * 1일차 오후 실습 2 — 버튼으로 모드 전환
 *
 *  1일차 오후 : 레벨 읽기와 에지 검출의 차이
 *  보드       : SW2~SW5 = PE4~PE7 (Active-Low, 외부 10kΩ 풀업)
 *  이 예제에서 "버튼이 늦게 먹는" 문제를 직접 겪는다. 해답은 2일차 오전.
 */
#define F_CPU 14745600UL

#include <util/delay.h>
#include "led.h"
#include "btn.h"

int main(void)
{
    uint8_t mode = 0;

    led_init();
    btn_init();

    while (1) {
        /* SW2 를 "누른 순간" 에만 모드를 바꾼다 (에지) */
        if (btn_get_edge(BTN_SW2)) {
            mode++;
            if (mode >= 3)
                mode = 0;
        }

        /* SW5 는 "누르고 있는 동안" LED7 을 켠다 (레벨) */
        if (btn_is_pressed(BTN_SW5))
            led_on(7);
        else
            led_off(7);

        switch (mode) {
        case 0:
            for (uint8_t n = 0; n < 7; n++) {   /* 여기서 0.7 초가 지나간다 */
                led_on(n); _delay_ms(100); led_off(n);
            }
            break;
        case 1:
            led_write(0x55); _delay_ms(300);
            led_write(0x2A); _delay_ms(300);
            break;
        case 2:
            led_write(0x00);
            break;
        }
    }
}

/*
 *  관찰할 것
 *   1) mode 0 에서 SW2 를 짧게 누르면 반응하지 않는 경우가 있다 — 왜인가
 *   2) SW5(레벨)은 잘 듣는데 SW2(에지)만 놓치는 이유는 무엇인가
 *   3) _delay_ms(100) 을 _delay_ms(10) 으로 줄이면 얼마나 나아지는가
 */
