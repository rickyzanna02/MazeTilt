// the setup routine runs once when you press reset:
void setup() {
  // initialize serial communication at 115200 bits per second:
  Serial.begin(115200);
}

// the loop routine runs over and over again forever:
void loop() {
  // read the input on A0, A1, A2:
  int x = analogRead(A0);
  int y = analogRead(A1);
  int z = analogRead(A2);
  // print out the value you read:
  Serial.print(x);
  Serial.print(",");
  Serial.print(y);
  Serial.print(",");
  Serial.println(z);
  delay(10);  // delay in between reads for stability
}