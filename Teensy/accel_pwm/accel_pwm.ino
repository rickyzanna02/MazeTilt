/*
  Teensy 3.6
  - Accelerometro su A0 A1 A2 -> Serial verso Pygame
  - ERM motor su pin 2 (PWM)
  - 'V'  = vibrazione impulsiva (muri)
  - 'H:x' = vibrazione continua (area buco)
*/

int motorPin = 2;

// ------------------ VIBRAZIONE IMPULSO ------------------
int impulsePower = 220;
unsigned long impulseTime = 120;
bool impulseActive = false;
unsigned long impulseStart = 0;

// ------------------ VIBRAZIONE CONTINUA ------------------
int holePower = 0;

// ------------------ ACCELEROMETRO ------------------
const int accelX = A0;
const int accelY = A1;
const int accelZ = A2;

unsigned long lastAccelSend = 0;
const unsigned long accelInterval = 10;

void setup() {
  pinMode(motorPin, OUTPUT);
  analogWrite(motorPin, 0);
  Serial.begin(115200);
}

void loop() {

  // -------- SERIAL INPUT --------
  while (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');

    // Impulso (muro)
    if (cmd == "V") {
      impulseActive = true;
      impulseStart = millis();
    }

    // Vibrazione area buco
    if (cmd.startsWith("H:")) {
      holePower = constrain(cmd.substring(2).toInt(), 0, 255);
    }
  }

  // -------- GESTIONE IMPULSO --------
  if (impulseActive && millis() - impulseStart > impulseTime) {
    impulseActive = false;
  }

  // -------- OUTPUT MOTORE --------
  int outputPower = max(
    impulseActive ? impulsePower : 0,
    holePower
  );

  analogWrite(motorPin, outputPower);

  // -------- INVIO ACCELEROMETRO --------
  if (millis() - lastAccelSend >= accelInterval) {
    lastAccelSend = millis();
    Serial.print(analogRead(accelX));
    Serial.print(",");
    Serial.print(analogRead(accelY));
    Serial.print(",");
    Serial.println(analogRead(accelZ));
  }
}
