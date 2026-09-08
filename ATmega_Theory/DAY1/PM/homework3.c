/*
 * homework3.c
 *
 * 1일차 오후 실습 3 — FND 에 숫자 띄우기
 *
 *  한 자리만 켜 보고, 그 다음에 네 자리를 돌린다.
 *  보드 : 세그먼트 PORTC (공통 애노드, 0 이 점등) · 자리 PD4~PD7 (1 이 선택)
 *
 *  아직 타이머가 없으므로 main 이 직접 _delay_ms 로 자리를 돌린다.
 *  이 루프가 도는 동안 다른 일을 할 수 없다는 것이 이 실습의 관찰 목표다.
 *  (3일차 오전에서 tick ISR 로 옮긴다 — D3AM/homework4.c)
 */
#define F_CPU 14745600UL

#include <util/delay.h>
#include "fnd.h"

int main(void)
{
    uint16_t value = 1234;

    fnd_init();

    /* ── 1단계 : 한 자리만 켜 본다 (주석을 풀고 확인) ─────────────
       while (1)
           fnd_digit(0, 8);              첫 자리에 8 이 계속 보인다
       ───────────────────────────────────────────────────────── */

    /* ── 2단계 : 네 자리를 돌린다 ─────────────────────────────── */
    while (1) {
        fnd_digit(0, (uint8_t)((value / 1000) % 10));   _delay_ms(3);
        fnd_digit(1, (uint8_t)((value /  100) % 10));   _delay_ms(3);
        fnd_digit(2, (uint8_t)((value /   10) % 10));   _delay_ms(3);
        fnd_digit(3, (uint8_t)( value         % 10));   _delay_ms(3);
    }
}

/*  확인할 것
 *    · 네 자리가 동시에 켜진 것처럼 보이는가
 *      (4자리 × 3 ms = 12 ms 주기 ≈ 83 Hz — 사람 눈은 60 Hz 이상이면 못 느낀다)
 *    · _delay_ms(3) 을 30 으로 바꾸면 한 자리씩 흐르는 것이 보인다
 *    · _delay_ms 를 빼면 잔상이 겹쳐 여덟 팔(8) 처럼 뭉개진다
 *
 *  여기서 생기는 문제
 *    · 이 루프가 도는 동안 버튼도 UART 도 끼워 넣을 자리가 없다
 *    · 3일차 오전 tick 이 이 문제를 푼다
 */
