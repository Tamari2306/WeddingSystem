import cv2
from datetime import datetime
from sqlalchemy.orm import Session
from models import Guest, SessionLocal  # Assuming you defined these in models.py

def scan_qr_code():
    session = SessionLocal()

    cap = cv2.VideoCapture(0)

    detector = cv2.QRCodeDetector()

    while True:
        ret, frame = cap.read()

        value, pts, qr_code = detector.detectAndDecode(frame)

        if value:
            print(f"QR Code detected: {value}")

            guest = session.query(Guest).filter_by(qr_code_id=value).first()

            if guest:
                if guest.has_entered:
                    print(f"❌ {guest.name} has already entered.")
                else:
                    print(f"Guest: {guest.name}, Entry Status: Not Entered")
                    validate = input("Allow entry for this guest? (y/n): ").strip().lower()
                    if validate == 'y':
                        guest.has_entered = True
                        guest.entry_time = datetime.now()
                        session.commit()
                        print(f"✅ {guest.name} marked as entered.")
                    else:
                        print("❌ Entry denied.")
            else:
                print("⚠️ Guest not found in the database.")

        cv2.imshow("QR Code Scanner", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    session.close()

# Run the scanner
scan_qr_code()
