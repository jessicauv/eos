#include <Adafruit_NeoPixel.h>

#define LED_PIN        D0
#define BUTTON_PIN     D1
#define NUM_LEDS       60
#define MAX_BRIGHTNESS 80   // ~30% to keep USB power safe
#define NUM_ZONES      4

// Zone n covers LEDs zoneStart[n-1] up to (not including) zoneStart[n]
const int zoneStart[NUM_ZONES + 1] = {0, 15, 30, 45, 60};

Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
String line;

bool lastButton = HIGH;
unsigned long lastChange = 0;
const unsigned long DEBOUNCE_MS = 50;

void fillRange(int from, int to, uint8_t r, uint8_t g, uint8_t b) {
  for (int i = from; i < to; i++) strip.setPixelColor(i, strip.Color(r, g, b));
  strip.show();
}

void idleGlow() { fillRange(0, NUM_LEDS, 8, 8, 14); }

void startupSweep() {
  for (int i = 0; i < NUM_LEDS; i++) {
    strip.setPixelColor(i, strip.Color(0, 60, 200));
    strip.show();
    delay(25);
  }
  delay(300);
  idleGlow();
}

void handleLine(const String& s) {
  int n, r, g, b;
  if (s == "OFF") {
    strip.clear();
    strip.show();
  } else if (s.startsWith("A,") &&
             sscanf(s.c_str(), "A,%d,%d,%d", &r, &g, &b) == 3) {
    fillRange(0, NUM_LEDS, r, g, b);
  } else if (s.startsWith("Z,") &&
             sscanf(s.c_str(), "Z,%d,%d,%d,%d", &n, &r, &g, &b) == 4 &&
             n >= 1 && n <= NUM_ZONES) {
    fillRange(zoneStart[n - 1], zoneStart[n], r, g, b);
  }
}

void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      line.trim();
      handleLine(line);
      line = "";
    } else {
      line += c;
    }
  }
}

void readButton() {
  bool reading = digitalRead(BUTTON_PIN);
  if (reading != lastButton && millis() - lastChange > DEBOUNCE_MS) {
    lastChange = millis();
    lastButton = reading;
    if (reading == LOW) Serial.println("START");   // pressed
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  strip.begin();
  strip.setBrightness(MAX_BRIGHTNESS);
  startupSweep();
  Serial.println("READY");
}

void loop() {
  readSerial();
  readButton();
}
