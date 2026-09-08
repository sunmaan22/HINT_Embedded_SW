/*
 * homework2.c
 *
 * 2일차 오후 실습 2 — 한 글자 명령 파서
 *
 *  PC 에서 글자 하나를 보내면 보드가 그에 맞게 동작하고 응답을 돌려준다.
 *  수신은 USART1_RX 인터럽트, 해석과 출력은 main — ISR 은 여전히 한 줄이다.
 *
 *  터미널 : 9600 · 8 · None · 1 · 흐름 제어 없음
 */
#define F_CPU 14745600UL

#include <avr/interrupt.h>
#include "led.h"
#include "uart.h"

static void handle_cmd(uint8_t c)
{
    switch (c) {
    /* led_write 는 "비트 1 = 점등" 이다 — 드라이버가 Active-Low 를 흡수한다 */
    case '1':  led_write(0xFF);  uart_puts("ALL ON\n");   break;
    case '0':  led_write(0x00);  uart_puts("ALL OFF\n");  break;
    case '?':  uart_puts("1 = on   0 = off\n");           break;
    default:   uart_puts("? try ?\n");                    break;
    }
}

int main(void)
{
    uint8_t rx;

    led_init();
    uart_init();
    sei();

    uart_puts("=== command parser ===\n");
    uart_puts("press ?\n");

    while (1) {
        if (uart_get_event(&rx) & UART_EVENT_RX)
            handle_cmd(rx);             /* 해석은 main 에서 */
    }
}

/*  확인할 것
 *    · 명령을 보낼 때마다 응답이 한 줄씩 돌아오는가
 *    · 아무 글자나 보내면 "? try ?" 가 나오는가
 *
 *  주의
 *    · handle_cmd 를 ISR 안에서 부르면 안 된다 — uart_puts 는 블로킹이다
 *    · 한 글자만 담기므로 빠르게 붙여 보내면 놓친다 (4.7 절 링 버퍼)
 */
