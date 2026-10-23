// SlothPlant: reads soil moisture and sends it to a laptop over WiFi.
// Board: Arduino UNO R4 WiFi (uses the built-in WiFiS3 library)
//
// Sensor reading approach based on the SunFounder soil moisture
// example (3-in-1 Kit). On this sensor, HIGHER numbers = DRIER soil
// (from class testing, readings above ~400 meant dry).

#include <WiFiS3.h>

// ---- CHANGE THESE LOCALLY (never commit your real WiFi details) ----
const char* WIFI_SSID = " "; //WiFi name
const char* WIFI_PASS = " "; //Wifi password
const char* SERVER_IP = " ";   // your laptop's IP on the same WiFi
const int   SERVER_PORT = 5000;

const int moisturePin = A0;   // Soil moisture sensor

const unsigned long SEND_EVERY_MS = 10000;  // 10 sec for testing; use 600000 (10 min) later
unsigned long lastSend = 0;

WiFiClient client;

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  while (WiFi.begin(WIFI_SSID, WIFI_PASS) != WL_CONNECTED) {
    Serial.print(".");
    delay(2000);
  }
  Serial.println("\nConnected!");
  Serial.print("Arduino IP: ");
  Serial.println(WiFi.localIP());
}

void sendReading(int soil) {
  String body = "{\"soil\":" + String(soil) + "}";

  if (client.connect(SERVER_IP, SERVER_PORT)) {
    client.println("POST /reading HTTP/1.1");
    client.print("Host: ");
    client.println(SERVER_IP);
    client.println("Content-Type: application/json");
    client.print("Content-Length: ");
    client.println(body.length());
    client.println("Connection: close");
    client.println();
    client.print(body);
    client.stop();
    Serial.println("Sent: " + body);
  } else {
    Serial.println("Could not reach laptop server");
  }
}

void setup() {
  Serial.begin(9600);
  connectWiFi();
}

void loop() {
  if (millis() - lastSend >= SEND_EVERY_MS) {
    lastSend = millis();
    int moisture = analogRead(moisturePin);
    Serial.println(moisture > 400 ? "Moisture low" : "Moisture good");
    sendReading(moisture);
  }
}
