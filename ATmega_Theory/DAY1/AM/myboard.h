/*
 * myboard.h — 보드 배선만 적는 파일 (SDK ATMEGA128A)
 *
 *  "어느 레지스터인가" 는 myreg.h 가, "무엇이 거기 달려 있는가" 는 여기가 맡는다.
 *  배선이 바뀌면 이 파일만 고치면 된다 — solutions_sw/board.h 와 같은 원칙이다.
 *
 *  LED D1~D8 : PB0 ~ PB7,  Active-Low
 *      +5V - 1kΩ - LED - PBn   이므로 핀이 0 일 때 켜진다.
 */

#ifndef MYBOARD_H_
#define MYBOARD_H_

#include "myreg.h"

#define LED_DDR         MY_DDRB
#define LED_PORT        MY_PORTB
#define LED_COUNT       8

#define LED_ALL_OUTPUT  0xFF        /* DDR 에 쓸 값 */
#define LED_ALL_ON      0x00        /* Active-Low 라 0 이 점등 */
#define LED_ALL_OFF     0xFF

#endif /* MYBOARD_H_ */
