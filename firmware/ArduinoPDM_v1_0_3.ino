/**************************************************************
 * Arduino CANbus – PDM-styrning med konfig + statusutskick
 * Författare: Jan Lindvall / ErRoR Engineering
 * FW Version 1.0.3 – med EEPROM-lagring av relayState[] + switchmap
 Licens: MIT
 **************************************************************/

#include <SPI.h>
#include <mcp_can.h>
#include <EEPROM.h>
#define FW_VERSION "1.0.3"

#define MAX_RELAYS 8
const int CAN_CS_PIN = 10;
const long CAN_SPEED = CAN_1000KBPS;
const int CAN_CLOCK = MCP_8MHZ;

const int relayPins[MAX_RELAYS] = {3, 4, 5, 6, 7, 8, 9, A0};
const int switchToRelayMap[MAX_RELAYS] = {
  4, // S1 
  3, // S2
  2, // S3 
  1, // S4
  0, // S5
  6, // S6 
  5, // S7 
  7  // S8
};

const unsigned long configCanId = 0x660;
const unsigned long configReplyId = 0x661;

const int EEPROM_ADDR_TOGGLE_MASK = 0;
const int EEPROM_ADDR_CANID = 1;
const int EEPROM_ADDR_STATUSRATE = 3;
const int EEPROM_ADDR_RELAYSTATE = 10;

MCP_CAN CAN(CAN_CS_PIN);

byte relayToggleMask = 0x00;
bool relayState[MAX_RELAYS] = {false};
byte previousSwitchMask = 0;

unsigned long listenCanId = 0x642;
unsigned long statusCanId = 0x650;
unsigned int statusInterval = 1000;
unsigned long lastStatusSend = 0;

void setup() {
  Serial.begin(115200);
  delay(500);

  if (CAN.begin(MCP_ANY, CAN_SPEED, CAN_CLOCK) == CAN_OK) {
    CAN.setMode(MCP_NORMAL);
  } else {
    while (1);
  }

  relayToggleMask = EEPROM.read(EEPROM_ADDR_TOGGLE_MASK);
  statusInterval = EEPROM.read(EEPROM_ADDR_STATUSRATE) | (EEPROM.read(EEPROM_ADDR_STATUSRATE + 1) << 8);
  if (statusInterval == 0xFFFF || statusInterval == 0) statusInterval = 1000;

  listenCanId = 0x642;

  for (int i = 0; i < MAX_RELAYS; i++) {
    pinMode(relayPins[i], OUTPUT);
    relayState[i] = EEPROM.read(EEPROM_ADDR_RELAYSTATE + i);
    digitalWrite(relayPins[i], relayState[i] ? LOW : HIGH);
  }

  byte ackMsg[6] = { 'P', 'D', 'M', ' ', 'O', 'K' };
  CAN.sendMsgBuf(0x6A0, 0, 6, ackMsg);
}

void loop() {
  handleCAN();
  sendCANStatus();
}

void handleCAN() {
  byte len = 0;
  byte buf[8];
  unsigned long canId = 0;

  if (CAN.checkReceive() == CAN_MSGAVAIL) {
    CAN.readMsgBuf(&canId, &len, buf);

    if (canId == listenCanId && len >= 5) {
      byte switchMask = buf[4];

      for (int i = 0; i < MAX_RELAYS; i++) {
        int relayIndex = switchToRelayMap[i];
        bool currentPressed = bitRead(switchMask, i);
        bool previousPressed = bitRead(previousSwitchMask, i);
        bool toggle = bitRead(relayToggleMask, i);

        if (toggle) {
          if (currentPressed && !previousPressed) {
            relayState[relayIndex] = !relayState[relayIndex];
            digitalWrite(relayPins[relayIndex], relayState[relayIndex] ? LOW : HIGH);
            EEPROM.update(EEPROM_ADDR_RELAYSTATE + relayIndex, relayState[relayIndex]);
          }
        } else {
          if (relayState[relayIndex] != currentPressed) {
            relayState[relayIndex] = currentPressed;
            digitalWrite(relayPins[relayIndex], currentPressed ? LOW : HIGH);
            EEPROM.update(EEPROM_ADDR_RELAYSTATE + relayIndex, relayState[relayIndex]);
          }
        }
      }
      previousSwitchMask = switchMask;
    }

    else if (canId == configCanId && len >= 1) {
      byte command = buf[0];
      byte reply[8] = {0};

      if (command == 0x01 && len >= 2) {
        relayToggleMask = buf[1];
        reply[0] = 0x00;
        reply[1] = command;

      } else if (command == 0x02) {
        EEPROM.write(EEPROM_ADDR_TOGGLE_MASK, relayToggleMask);
        EEPROM.write(EEPROM_ADDR_CANID, lowByte(listenCanId));
        EEPROM.write(EEPROM_ADDR_CANID + 1, highByte(listenCanId));
        EEPROM.write(EEPROM_ADDR_STATUSRATE, lowByte(statusInterval));
        EEPROM.write(EEPROM_ADDR_STATUSRATE + 1, highByte(statusInterval));
        reply[0] = 0x00;
        reply[1] = command;

      } else if (command == 0x03) {
        reply[0] = 0x00;
        reply[1] = command;
        reply[2] = relayToggleMask;
        reply[3] = lowByte(listenCanId);
        reply[4] = highByte(listenCanId);
        reply[5] = lowByte(statusInterval);
        reply[6] = highByte(statusInterval);

      } else if (command == 0x04 && len >= 3) {
        listenCanId = buf[1] | (buf[2] << 8);
        reply[0] = 0x00;
        reply[1] = command;

      } else if (command == 0x05 && len >= 3) {
        statusInterval = buf[1] | (buf[2] << 8);
        reply[0] = 0x00;
        reply[1] = command;

      } else if (command == 0x06) {
        reply[0] = 0x00;
        reply[1] = command;
        reply[2] = '1';
        reply[3] = '.';
        reply[4] = '0';
        reply[5] = '.';
        reply[6] = '3';
        reply[7] = 0;

      } else {
        reply[0] = 0xFF;
        reply[1] = command;
      }

      CAN.sendMsgBuf(configReplyId, 0, 8, reply);
    }
  }
}

void sendCANStatus() {
  if (millis() - lastStatusSend >= statusInterval) {
    lastStatusSend = millis();
    byte relayMask = 0x00;
    for (int i = 0; i < MAX_RELAYS; i++) bitWrite(relayMask, i, relayState[i]);
    byte outBuf[8] = { relayMask, 0,0,0,0,0,0,0 };
    CAN.sendMsgBuf(statusCanId, 0, 8, outBuf);
  }
}
