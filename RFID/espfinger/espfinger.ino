/* ESP32 Code to Receive RFID and Fingerprint UID */
#include <WiFi.h>
#include <HTTPClient.h>

// WiFi credentials
const char* ssid = "Deep";
const char* password = "deep0407";

// Flask server details
const char* server_url = "http://192.168.219.29:5000/update_uid";

// ESP32 UART2 pins
#define RXD2 16 // ESP32 RX pin
#define TXD2 17 // ESP32 TX pin

void setup() {
  Serial.begin(115200); // ESP32 Serial Monitor
  Serial2.begin(115200, SERIAL_8N1, RXD2, TXD2); // UART2 for communication with Arduino

  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi!");
}

void loop() {
  // Check if data is available from Arduino
  if (Serial2.available()) {
    String receivedData = Serial2.readStringUntil('\n'); // Read data from Arduino
    receivedData.trim(); // Remove unwanted newline or spaces
    Serial.print("Received: ");
    Serial.println(receivedData);

    String dataType = receivedData.substring(0, receivedData.indexOf(':'));
    String dataValue = receivedData.substring(receivedData.indexOf(':') + 1);

    String payload;
    if (dataType == "RFID") {
      payload = "{\"rfid_uid\":\"" + dataValue + "\"}";
    } else if (dataType == "FINGER") {
      payload = "{\"fingerprint_uid\":\"" + dataValue + "\"}";
    } else {
      return;
    }

    // Send UID to Flask server
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(server_url);
      http.addHeader("Content-Type", "application/json");
      int httpResponseCode = http.POST(payload);
      if (httpResponseCode > 0) {
        Serial.println("Data sent successfully!");
      } else {
        Serial.println("Error sending data");
      }
      http.end();
    }
  }
}
