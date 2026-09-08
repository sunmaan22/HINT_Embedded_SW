/*
 * homework1.c
 *
 * 2일차 오후 실습 1 — 인터럽트를 로그로 검증
 *
 *  2일차 오후 : USART1 · 폴링 송신 · 인터럽트 수신
 *  보드       : RXD1=PD2, TXD1=PD3 -> FT232RL -> USB Micro 5P
 *  준비       : USB 케이블로 PC 연결 -> 장치 관리자에서 COM 번호 확인
 *               PuTTY  9600 / 8 / None / 1 / Flow control None
 *
 *  인터럽트로 도는 코드는 눈으로 볼 수 없다. 그것을 보이게 만드는 것이 목적.
 *  버튼을 누를 때마다 한 줄씩 찍는다 — 그게 전부다.
 */
#define F_CPU 14745600UL

#include <avr/interrupt.h>
#include "btn.h"
#include "uart.h"

int main(void)
{
    uint8_t  ev;
    uint16_t count = 0;

    btn_init();
    btn_int_enable();
    uart_init();

    sei();

    uart_puts("\n=== SDK ATmega128A  UART1 log ===\n");

    while (1) {
        ev = btn_get_events();          /* ISR 이 설정해 둔 비트를 받는다 */

        if (ev) {
            uart_puts("BTN event = ");
            uart_put_hex8(ev);          /* 어느 버튼인지 비트로 */
            uart_puts("  count=");
            uart_put_uint16(++count);
            uart_puts("\n");
        }
    }
}

/*
 *  확인할 것
 *   1) 문자가 깨지면 F_CPU 와 보레이트 설정을 먼저 의심한다
 *      14.7456 MHz · 9600 -> UBRR1 = 95 (오차 0 %)
 *   2) 버튼마다 event 값이 다른가 (SW2=0x01 · SW3=0x02 · SW4=0x04 · SW5=0x08)
 *   3) 채터링을 로그로 세어 본다 — 한 번 눌렀을 때 count 가 몇 올라가는가
 */
