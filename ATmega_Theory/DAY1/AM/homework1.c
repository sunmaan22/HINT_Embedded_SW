/*
 * homework1.c
 *
 * 1일차 오전 실습 — 주소로만 LED 켜기
 *
 *  1일차 오전 : Memory-mapped I/O 와 포인터 접근
 *  보드       : SDK ATMEGA128A — LED D1~D8 이 PB0~PB7 에 Active-Low 로 달려 있다
 *
 *  프로젝트에 함께 넣을 파일
 *      myreg.h     레지스터 주소와 REG8 매크로   (1.5 절에서 만든 것)
 *      myboard.h   보드 배선 — LED 가 어디에 어떤 극성으로 달려 있는가
 *
 *  <avr/io.h> 는 쓰지 않는다. 이름은 전부 우리가 붙인 것이다.
 *  main 에 0x37 · 0x38 같은 숫자가 하나도 남지 않는 것이 이 예제의 핵심이다.
 */
#include "myboard.h"

int main(void)
{
    LED_DDR  = LED_ALL_OUTPUT;      /* PB0 ~ PB7 을 모두 출력으로 */
    LED_PORT = LED_ALL_ON;          /* Active-Low -> LED 8개 전부 점등 */

    while (1) {
        /* 아무것도 하지 않는다. main 은 절대 끝나면 안 된다 */
    }
}

/*
 *  확인할 것
 *   1) I/O View 에서 DDRB = 0xFF, PORTB = 0x00 인지 본다
 *   2) myreg.h 의 REG8 에서 volatile 을 빼고 -O2 로 빌드한 뒤
 *      .lss 에서 out 명령이 남는지 확인
 *   3) <avr/io.h> 를 include 하고 DDRB / PORTB 로 바꿔도 결과가 같은지 본다
 *   4) myboard.h 의 LED_ALL_ON 을 0xFF 로 바꾸면 어떻게 되는지 예상하고 확인
 */
