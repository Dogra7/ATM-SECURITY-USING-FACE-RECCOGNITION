#include <WiFi.h>
#include <HTTPClient.h>
#include <MFRC522.h>
#include <SPI.h>

// WiFi credentials
const char* ssid = "Sunny";
const char* password = "lkjhgfdsa";

// Flask server details
const char* server_url = "http://192.168.100.4:5000/update_uid";

// RFID pins
#define RST_PIN 22
#define SS_PIN 5
MFRC522 mfrc522(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi!");
}

void loop() {
  // Check for RFID card
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String rfidUID = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      rfidUID += String(mfrc522.uid.uidByte[i], HEX);
    }
    rfidUID.toUpperCase();
    Serial.println("Scanned UID: " + rfidUID);

    // Send UID to Flask server
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(server_url);
      http.addHeader("Content-Type", "application/json");
      String payload = "{\"rfid_uid\":\"" + rfidUID + "\"}";
      int httpResponseCode = http.POST(payload);
      if (httpResponseCode > 0) {
        Serial.println("UID sent successfully!");
      } else {
        Serial.println("Error sending UID");
      }
      http.end();
    }
  }

  delay(1000); // Avoid spamming the server
}
