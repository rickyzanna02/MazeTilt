/*
  Teensy 3.6
  Accelerometro + ERM motors
  Comunicazione seriale con Pure Data
*/

#include <string.h>

#define BAUD_RATE 115200
#define ANALOG_BIT_RESOLUTION 12   // 0–4095

// ------------------ MOTORI ------------------
const int motorPin1 = A8;
const int motorPin2 = A9;

// Vibrazione impulso
int impulsePower = 200;
unsigned long impulseTime = 120;
bool impulseActive = false;
unsigned long impulseStart = 0;

// Vibrazione continua
int holePower = 0;

// ------------------ ACCELEROMETRO ------------------
const int accelX = A0;
const int accelY = A1;
const int accelZ = A2;

unsigned long lastAccelSend = 0;
const unsigned long accelInterval = 10;

// ------------------ SERIAL PARSER (PD) ------------------
const byte MAX_MSG = 64;
char receivedMsg[MAX_MSG];

const char START_MARKER = '[';
const char END_MARKER   = ']';

bool newMsg = false;

// ------------------------------------------------------

void receiveMessage() {

  static bool receptionInProgress = false;
  static byte idx = 0;
  char c;

  while (Serial.available() > 0 && !newMsg) {

    c = Serial.read();

    if (receptionInProgress) {

      if (c != END_MARKER) {
        receivedMsg[idx++] = c;
        if (idx >= MAX_MSG) idx = MAX_MSG - 1;
      } 
      else {
        receivedMsg[idx] = '\0';
        receptionInProgress = false;
        idx = 0;
        newMsg = true;
      }

    } 
    else if (c == START_MARKER) {
      receptionInProgress = true;
    }
  }

  if (newMsg) {
    handleMessage(receivedMsg);
    newMsg = false;
  }
}

// ------------------------------------------------------

void handleMessage(char *msg) {

  // Token: COMANDO, VALORE
  char *command;
  char *value;

  const char delimiters[] = ", ";

  command = strtok(msg, delimiters);
  value   = strtok(NULL, delimiters);

  if (!command || !value) return;

  // -------- IMPULSO --------
  if (strcmp(command, "V") == 0 && atoi(value) == 1) {
    impulseActive = true;
    impulseStart = millis();
  }

  // -------- VIBRAZIONE CONTINUA --------
  if (strcmp(command, "H") == 0) {
    holePower = constrain(atoi(value), 0, 255);
  }
}

// ------------------------------------------------------

void setup() {

  pinMode(motorPin1, OUTPUT);
  pinMode(motorPin2, OUTPUT);

  analogWrite(motorPin1, 0);
  analogWrite(motorPin2, 0);

  analogReadResolution(ANALOG_BIT_RESOLUTION);

  Serial.begin(BAUD_RATE);
  while (!Serial);
}

// ------------------------------------------------------

void loop() {

  receiveMessage();

  // ----- gestione impulso -----
  if (impulseActive && millis() - impulseStart > impulseTime) {
    impulseActive = false;
  }

  int outputPower = max(
    impulseActive ? impulsePower : 0,
    holePower
  );

  analogWrite(motorPin1, outputPower);
  analogWrite(motorPin2, outputPower);

  // ----- invio accelerometro -----
  if (millis() - lastAccelSend >= accelInterval) {
    lastAccelSend = millis();

    Serial.print("a0, ");
    Serial.println(analogRead(accelX));

    Serial.print("a1, ");
    Serial.println(analogRead(accelY));

    Serial.print("a2, ");
    Serial.println(analogRead(accelZ));
  }
}