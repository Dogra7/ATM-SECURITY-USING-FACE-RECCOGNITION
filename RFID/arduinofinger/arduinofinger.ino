/* Arduino Code for RFID and AS608 Fingerprint Sensor */
#include <SPI.h>
#include <MFRC522.h>
#include <SoftwareSerial.h>
#include <Adafruit_Fingerprint.h>

#define RST_PIN  9
#define SS_PIN   10
#define RX_PIN   2   // SoftwareSerial RX pin for ESP32
#define TX_PIN   3   // SoftwareSerial TX pin for ESP32
#define FP_RX    4   // SoftwareSerial RX pin for Fingerprint Sensor
#define FP_TX    5   // SoftwareSerial TX pin for Fingerprint Sensor

MFRC522 mfrc522(SS_PIN, RST_PIN);  // Create MFRC522 instance
SoftwareSerial mySerial(RX_PIN, TX_PIN); // RX, TX for ESP32
SoftwareSerial fingerSerial(FP_RX, FP_TX); // RX, TX for AS608 Fingerprint Sensor
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&fingerSerial);

void setup() {
  Serial.begin(9600); // Debugging
  mySerial.begin(115200); // Communication with ESP32
  fingerSerial.begin(57600); // Fingerprint sensor baud rate
  SPI.begin();
  mfrc522.PCD_Init();
  
  // Initialize Fingerprint Sensor
  finger.begin(57600);
  if (finger.verifyPassword()) {
    Serial.println("Fingerprint sensor detected!");
  } else {
    Serial.println("Fingerprint sensor not found!");
    while (1);
  }
}

void loop() {
  // Check for RFID Card
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String uidString = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      uidString += String(mfrc522.uid.uidByte[i], HEX);
    }
    uidString.toUpperCase();
    Serial.println("RFID UID: " + uidString);
    mySerial.println("RFID:" + uidString);
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
  }

  // Check for Fingerprint
  Serial.println("Place Finger...");
  int id = getFingerprintID();
  if (id > 0) {
    Serial.print("Fingerprint ID: ");
    Serial.println(id);
    mySerial.println("FINGER:" + String(id));
  }
  delay(1000);
}

int getFingerprintID() {
  int p = finger.getImage();
  if (p != FINGERPRINT_OK) return -1;

  p = finger.image2Tz();
  if (p != FINGERPRINT_OK) return -1;

  p = finger.fingerFastSearch();
  if (p != FINGERPRINT_OK) return -1;

  return finger.fingerID;
}