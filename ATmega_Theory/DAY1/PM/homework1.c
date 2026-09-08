/*
 * homework1.c
 *
 * 1일차 오후 실습 1 — LED 패턴 만들기 (드라이버만 사용)
 *
 *  1일차 오후 : app / driver / register 3계층
 *  프로젝트에 drivers/led.c 를 함께 추가해야 한다.
 *  main 에 PORTB 라는 글자가 하나도 없는 것이 이 예제의 핵심이다.
 */
#define F_CPU 14745600UL

#include <util/delay.h>
#include "led.h"

static void pattern_sequential(void)
{
    for (uint8_t n = 0; n < 8; n++) {
        led_on(n);
        _delay_ms(120);
        led_off(n);
    }
}

static void pattern_pingpong(void)
{
    for (uint8_t n = 0; n < 8; n++)      { led_on(n); _delay_ms(90); led_off(n); }
    for (int8_t  n = 6; n > 0; n--)      { led_on((uint8_t)n); _delay_ms(90);
                                           led_off((uint8_t)n); }
}

static void pattern_alternate(void)
{
    for (uint8_t k = 0; k < 6; k++) {
        led_write(0x55);                 /* 비트 1 = 점등 (드라이버가 반전) */
        _delay_ms(150);
        led_write(0xAA);
        _delay_ms(150);
    }
    led_write(0x00);
}

int main(void)
{
    led_init();

    while (1) {
        pattern_sequential();
        pattern_pingpong();
        pattern_alternate();
    }
}
