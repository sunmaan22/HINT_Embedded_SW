/*
 * lcd.c
 *
 * Created: 2026-09-16 오후 7:56:54
 * Author: Incheol Shin
 */ 

#ifndef F_CPU
#define F_CPU 14745600UL
#endif

#include <avr/io.h>
#include <util/delay.h>

#include "lcd.h"

/*--------------------------------------------------
 * LCD Enable Pulse
 *--------------------------------------------------*/
static void lcd_epulse(void) {
   PORTG |= (1 << E);
   _delay_us(1);
   PORTG &= ~(1 << E);
}

/*--------------------------------------------------
 * LCD Busy Flag Check
 *
 * RS = 0
 * RW = 1
 * DB7 = Busy Flag
 *
 * BF = 1 : LCD busy
 * BF = 0 : LCD ready
 *--------------------------------------------------*/
static void lcd_busy(void) {
   uint8_t busy;

   /*
    * PORTA를 입력으로 변경
    * PORTA = 0으로 하여 내부 Pull-up 비활성화
    */
   PORTA = 0x00;
   DDRA  = 0x00;

   /* E = 0 */
   PORTG &= ~(1 << E);

   /* RS = 0 : Instruction register */
   PORTG &= ~(1 << RS);

   /* RW = 1 : Read */
   PORTG |= (1 << RW);

   do {
      /*
       * E = 1일 때 LCD의 데이터가
       * DB0~DB7에 출력됨
       */
      PORTG |= (1 << E);

      _delay_us(1);

      /*
       * DB7 = Busy Flag
       */
      busy = PINA & 0x80;

      /*
       * E = 0
       */
      PORTG &= ~(1 << E);

      _delay_us(1);

   } while (busy);

   /*
    * 다시 Write 모드
    */
   PORTG &= ~(1 << RW);

   /*
    * PORTA를 출력으로 변경
    */
   DDRA = 0xFF;
}

/*--------------------------------------------------
 * LCD Command
 *
 * RS = 0
 * RW = 0
 *--------------------------------------------------*/
void lcd_command(uint8_t cmd) {
   lcd_busy();

   /*
    * Command 데이터 출력
    */
   PORTA = cmd;

   /*
    * RS = 0 : Command
    */
   PORTG &= ~(1 << RS);

   /*
    * RW = 0 : Write
    */
   PORTG &= ~(1 << RW);

   lcd_epulse();
}

/*--------------------------------------------------
 * LCD Data
 *
 * RS = 1
 * RW = 0
 *--------------------------------------------------*/
void lcd_data(uint8_t data) {
   lcd_busy();

   /*
    * 문자 데이터 출력
    */
   PORTA = data;

   /*
    * RS = 1 : Data
    */
   PORTG |= (1 << RS);

   /*
    * RW = 0 : Write
    */
   PORTG &= ~(1 << RW);

   lcd_epulse();
}

/*--------------------------------------------------
 * LCD Initialization
 *
 * 8bit
 * 2 Line
 * Display ON
 * Cursor ON
 * Blink ON
 *--------------------------------------------------*/
void lcd_init(void) {
   /*
    * PORTA : LCD Data D0~D7
    */
   DDRA = 0xFF;

   /*
    * PORTG : RS, RW, E
    */
   DDRG |= (1 << RS) |
         (1 << RW) |
         (1 << E);

   /*
    * RS = 0
    * RW = 0
    * E  = 0
    */
   PORTG &= ~((1 << RS) |
            (1 << RW) |
            (1 << E));

   /*
    * 전원 공급 후 LCD 안정화
    * 최소 15ms 이상
    */
   _delay_ms(20);

   /*--------------------------------------------------
    * LCD Wake-up Sequence
    *
    * 이 시점에는 Busy Flag를 사용할 수 없음
    *--------------------------------------------------*/

   PORTA = 0x30;

   /*
    * Function Set
    * 8-bit interface
    */
   lcd_epulse();

   /*
    * 첫 번째 Function Set 이후
    * 최소 4.1ms
    */
   _delay_ms(5);

   /*
    * 두 번째 Function Set
    */
   lcd_epulse();

   /*
    * 최소 100us 이상
    */
   _delay_us(200);

   /*
    * 세 번째 Function Set
    */
   lcd_epulse();

   _delay_us(200);

   /*
    * 이제 Busy Flag 사용 가능
    */

   /*--------------------------------------------------
    * Function Set
    *
    * 0011 1000 = 0x38
    *
    * DL = 1 : 8 bit
    * N  = 1 : 2 line
    * F  = 0 : 5x8 font
    *--------------------------------------------------*/
   lcd_command(
      (1 << FUNCTION_SET) |
      (1 << F_DL) |
      (1 << F_N)
   );

   /*--------------------------------------------------
    * Display OFF
    *
    * 0000 1000 = 0x08
    *--------------------------------------------------*/
   lcd_command(1 << DISPLAY_ONOFF);

   /*--------------------------------------------------
    * Clear Display
    *
    * 0000 0001 = 0x01
    *--------------------------------------------------*/
   lcd_command(1 << CLEAR_DISPLAY);

   /*--------------------------------------------------
    * Entry Mode Set
    *
    * 0000 0110 = 0x06
    *
    * I/D = 1 : cursor right
    * S   = 0 : no display shift
    *--------------------------------------------------*/
   lcd_command(
      (1 << ENTRY_MODE) |
      (1 << E_ID)
   );

   /*--------------------------------------------------
    * Display ON/OFF Control
    *
    * 0000 1111 = 0x0F
    *
    * D = 1 : Display ON
    * C = 1 : Cursor ON
    * B = 1 : Blink ON
    *--------------------------------------------------*/
   lcd_command(
      (1 << DISPLAY_ONOFF) |
      (1 << D_D) |
      (1 << D_C) |
      (1 << D_B)
   );
}

/*--------------------------------------------------
 * Clear LCD
 *--------------------------------------------------*/
void lcd_clear(void) {
   lcd_command(1 << CLEAR_DISPLAY);
}

/*--------------------------------------------------
 * Cursor Home
 *--------------------------------------------------*/
void lcd_home(void)
{
   lcd_command(1 << RETURN_HOME);
}

/*--------------------------------------------------
 * Cursor Position
 *
 * x : 0 ~ 15
 * y : 0 ~ 1
 *
 * 1 Line : 0x00 ~
 * 2 Line : 0x40 ~
 *--------------------------------------------------*/
void lcd_gotoxy(uint8_t x, uint8_t y) {
   uint8_t address;

   if (y == 0) {
      address = x;
   }
   else {
      address = 0x40 + x;
   }

   lcd_command((1 << SET_DDRAM) | address);
}

/*--------------------------------------------------
 * String Output
 *--------------------------------------------------*/
void lcd_string(const char *str)
{
   while (*str != '\0') {
      lcd_data(*str);

      str++;
   }
}