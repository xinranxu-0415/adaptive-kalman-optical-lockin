// 16-722 final project: recorder (lock-in test signals + noise LED)
//
// Wiring (same as Lab 3):
//   D9  -> 220 ohm -> red LED   (signal, far from the LDR)
//   D10 -> 220 ohm -> white LED (noise, close to the LDR)
//   A0  <- LDR / 10k divider
//
// The PC sends ONE character to start a run:
//   K = calibration: white LED steady at WHITE_FIXED, red steps 0,50,100,150,200,255 (15 s each) -> 90 s
//   N = noise run:   red fixed at 150, white LED noise on                                          -> 60 s
//   1 = large steps   2 = small steps   3 = triangle ramp   4 = slow sine   5 = random walk
//       (white LED noise on)                                                                       -> 60 s each
//
// Output, one CSV line every 5 ms (200 Hz), same format as Lab 3:
//   ms, adc8, ref, level, noise
//   adc8 = sum of 8 readings of A0 (divide by 8 to get 0..1023)
//   ref  = +1/-1 carrier reference (2 Hz square wave)
//   level= commanded red LED amplitude (PWM 0..255)  -> ground truth after calibration
//   noise= commanded white LED PWM

const uint8_t SIG = 9;
const uint8_t NOI = 10;
const uint8_t DET = A0;

const unsigned long TS_US = 5000;            // 200 Hz
const unsigned long CARRIER_HALF_MS = 250;   // 2 Hz carrier
const unsigned long WARMUP_MS = 3000;        // run but do not record
const unsigned long NOISE_UPDATE_MS = 40;

// White-LED noise settings (narrow range chosen from the operating-point sweep)
const int WHITE_FIXED = 30;                  // steady white level in calibration run K
const int RW_MIN = 20;
const int RW_MAX = 40;
const int RW_STEP = 2;                       // random-walk step per update
const int WHITE_AMP = 5;                     // fast flicker, +/- this much

unsigned long durationMs(char m) { return (m == 'K') ? 90000UL : 60000UL; }

int stepLevel(const int *L, unsigned long t, unsigned long stepMs, int n) {
  unsigned long k = t / stepMs;
  if (k >= (unsigned long)n) k = n - 1;
  return L[k];
}

int levelAt(char m, unsigned long t, int walk) {
  static const int LK[6] = {0, 50, 100, 150, 200, 255};
  static const int L1[6] = {60, 255, 60, 255, 150, 60};
  static const int L2[6] = {120, 160, 200, 160, 120, 80};
  switch (m) {
    case 'K': return stepLevel(LK, t, 15000UL, 6);
    case 'N': return 150;
    case '1': return stepLevel(L1, t, 10000UL, 6);
    case '2': return stepLevel(L2, t, 10000UL, 6);
    case '3': {                               // triangle: 50 -> 255 -> 50 over 60 s
      float x = (float)t / 60000.0;
      float tri = 1.0 - fabs(2.0 * x - 1.0);
      return (int)(50 + 205 * tri);
    }
    case '4': return (int)(152 + 100 * sin(2 * PI * (float)t / 20000.0));  // 20 s period
    case '5': return walk;
  }
  return 0;
}

void setup() {
  Serial.begin(115200);
  pinMode(SIG, OUTPUT);
  pinMode(NOI, OUTPUT);
  analogWrite(SIG, 0);
  analogWrite(NOI, 0);
  randomSeed(analogRead(A5));
  Serial.println("# READY");
}

void loop() {
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'K' || c == 'N' || (c >= '1' && c <= '5')) runExperiment(c);
  }
}

void runExperiment(char mode) {
  const unsigned long total_ms = WARMUP_MS + durationMs(mode);
  Serial.print("# MODE ");
  Serial.println(mode);
  Serial.println("ms,adc8,ref,level,noise");

  unsigned long t0 = millis();
  unsigned long next_us = micros();
  unsigned long next_noise_ms = 0;
  unsigned long next_walk_ms = WARMUP_MS;
  int noise_level = 0;
  int rw = 30;
  int walk = 150;

  while (true) {
    unsigned long t = millis() - t0;
    if (t >= total_ms) break;
    unsigned long t_rec = (t > WARMUP_MS) ? (t - WARMUP_MS) : 0;

    if (t >= next_walk_ms) {                  // random walk of the red level (mode 5)
      walk += random(-20, 21);
      walk = constrain(walk, 40, 255);
      next_walk_ms = t + 500;
    }
    int level = constrain(levelAt(mode, t_rec, walk), 0, 255);

    int8_t ref = ((t / CARRIER_HALF_MS) % 2 == 0) ? 1 : -1;
    analogWrite(SIG, (ref > 0) ? level : 0);

    if (mode == 'K') {
      noise_level = WHITE_FIXED;
      analogWrite(NOI, noise_level);
    } else if (t >= next_noise_ms) {
      rw += random(-RW_STEP, RW_STEP + 1);
      rw = constrain(rw, RW_MIN, RW_MAX);
      int v = rw + random(-WHITE_AMP, WHITE_AMP + 1);
      noise_level = constrain(v, 0, 255);
      analogWrite(NOI, noise_level);
      next_noise_ms = t + NOISE_UPDATE_MS;
    }

    next_us += TS_US;
    while ((long)(micros() - next_us) < 0) { }

    unsigned int sum = 0;
    for (uint8_t i = 0; i < 8; i++) sum += analogRead(DET);

    if (t >= WARMUP_MS) {
      Serial.print(t - WARMUP_MS); Serial.print(',');
      Serial.print(sum); Serial.print(',');
      Serial.print((int)ref); Serial.print(',');
      Serial.print(level); Serial.print(',');
      Serial.println(noise_level);
    }
  }
  analogWrite(SIG, 0);
  analogWrite(NOI, 0);
  Serial.println("# DONE");
}
