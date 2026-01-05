/*
  Teensy 3.6
  - Accelerometro su A0 A1 A2 -> Serial verso Pygame
  - ERM motor su pin 2 (PWM)
  - Comando 'V' da Serial per vibrare
*/

int motorPin = 2;

// Vibrazione
int vibrationPower = 200;            // 0–255
unsigned long vibrationTime = 150;   // ms
bool vibrating = false;
unsigned long vibrationStart = 0;

// Accelerometro
const int accelX = A0;
const int accelY = A1;
const int accelZ = A2;

unsigned long lastAccelSend = 0;
const unsigned long accelInterval = 10; // ms (100 Hz)

void setup() {
  pinMode(motorPin, OUTPUT);
  analogWrite(motorPin, 0);

  Serial.begin(115200);
}

void loop() {

  /* ---------- RICEZIONE COMANDI DA PYGAME ---------- */
  while (Serial.available() > 0) {
    char cmd = Serial.read();

    if (cmd == 'V') {   // vibrazione
      analogWrite(motorPin, vibrationPower);
      vibrating = true;
      vibrationStart = millis();
    }
  }

  /* ---------- GESTIONE TIMER VIBRAZIONE ---------- */
  if (vibrating && millis() - vibrationStart >= vibrationTime) {
    analogWrite(motorPin, 0);
    vibrating = false;
  }

  /* ---------- INVIO DATI ACCELEROMETRO ---------- */
  if (millis() - lastAccelSend >= accelInterval) {
    lastAccelSend = millis();

    int x = analogRead(accelX);
    int y = analogRead(accelY);
    int z = analogRead(accelZ);

    // formato CSV: x,y,z\n
    Serial.print(x);
    Serial.print(",");
    Serial.print(y);
    Serial.print(",");
    Serial.println(z);
  }
}