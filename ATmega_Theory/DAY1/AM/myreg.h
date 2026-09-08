/*
 * myreg.h — <avr/io.h> 없이 쓰는 레지스터 이름
 *
 *  1일차 오전 1.5 절에서 손으로 만들어 본 매크로를 헤더로 옮긴 것이다.
 *  <avr/io.h> 가 내부에서 하는 일과 완전히 같다.
 *  다른 점은 주소를 우리가 데이터시트에서 직접 찾아 적었다는 것뿐이다.
 *
 *  주소 규칙 :  메모리 주소 = I/O 주소 + 0x20   (avr-libc 의 __SFR_OFFSET)
 *
 *      레지스터   I/O 주소   메모리 주소
 *      PINB       0x16       0x36
 *      DDRB       0x17       0x37
 *      PORTB      0x18       0x38
 */

#ifndef MYREG_H_
#define MYREG_H_

#include <stdint.h>

/* 주소 하나를 8비트 레지스터로 다룬다 — <avr/io.h> 의 _MMIO_BYTE 와 같다 */
#define REG8(addr)      (*(volatile uint8_t *)(addr))

/* I/O 주소로 적고 싶을 때 — <avr/io.h> 의 _SFR_IO8 과 같다 */
#define IO_OFFSET       0x20
#define IOREG8(io)      REG8((io) + IO_OFFSET)

/* ---------------------------------------------------------- PORTB */
#define MY_PINB         IOREG8(0x16)
#define MY_DDRB         IOREG8(0x17)
#define MY_PORTB        IOREG8(0x18)

/* ---------------------------------------------------------- 과제 1
 *  데이터시트 Register Summary 에서 PORTC 쪽 I/O 주소를 찾아
 *  아래 주석을 풀고 0x?? 자리를 채운다.
 */
/* #define MY_PINC      IOREG8(0x??) */
/* #define MY_DDRC      IOREG8(0x??) */
/* #define MY_PORTC     IOREG8(0x??) */

#endif /* MYREG_H_ */
