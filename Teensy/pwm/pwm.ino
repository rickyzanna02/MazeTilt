/*
  The analogWrite(pin, value) function uses PWM
*/

int pin = 2;         // the PWM pin

// the setup routine runs once when you press reset:
void setup() {
  // declare pin 2 to be an output:
  pinMode(pin, OUTPUT);
}

// the loop routine runs over and over again forever:
void loop() {
  // set the brightness of pin 9:
  analogWrite(pin, 0);
  delay(3000);

  analogWrite(pin, 100);
  delay(3000);

  analogWrite(pin, 160);
  delay(3000);

  analogWrite(pin, 255);
  delay(3000);
}