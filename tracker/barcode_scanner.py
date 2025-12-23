import cv2
from pyzbar.pyzbar import decode
import time
import easyocr
import re
from datetime import datetime

def scan_barcode():
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)  # width
    cap.set(4, 480)  # height

    barcode_data = None

    while True:
        success, img = cap.read()
        for barcode in decode(img):
            barcode_data = barcode.data.decode('utf-8')
            print("Barcode Detected:", barcode_data)
            time.sleep(2)
            cap.release()
            cv2.destroyAllWindows()
            return barcode_data

        cv2.imshow("Scan Barcode", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return None


def scan_expiry_date():
    """
    Capture an image from the camera and use EasyOCR to extract expiry date text.
    Returns the expiry date string if found and valid, else None.
    """
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)  # width
    cap.set(4, 480)  # height

    reader = easyocr.Reader(['en'], gpu=False)  # Initialize EasyOCR reader

    expiry_date = None
    print("Position the expiry date in front of the camera and press 'c' to capture.")

    while True:
        success, img = cap.read()
        cv2.imshow("Scan Expiry Date - Press 'c' to capture", img)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('c'):
            # Capture the frame for OCR
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            result = reader.readtext(gray)

            # Combine all detected text
            detected_text = " ".join([res[1] for res in result])
            print("Detected Text:", detected_text)

            # Regex to find date patterns like 4 MAR 2024 or 04/03/2024 etc.
            date_patterns = [
                r'(\d{1,2}\s*[A-Za-z]{3,9}\s*\d{4})',  # e.g. 4 MAR 2024
                r'(\d{1,2}/\d{1,2}/\d{2,4})',           # e.g. 04/03/2024
                r'(\d{4}-\d{1,2}-\d{1,2})'              # e.g. 2024-03-04
            ]

            for pattern in date_patterns:
                match = re.search(pattern, detected_text)
                if match:
                    date_str = match.group(1)
                    try:
                        # Try parsing the date string with multiple formats
                        for fmt in ("%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
                            try:
                                parsed_date = datetime.strptime(date_str, fmt)
                                # Check if year is realistic (e.g. between 2000 and 2100)
                                if 2000 <= parsed_date.year <= 2100:
                                    expiry_date = parsed_date.strftime("%d %b %Y")
                                    break
                            except ValueError:
                                continue
                        if expiry_date:
                            break
                    except Exception as e:
                        print("Date parsing error:", e)
            break
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    return expiry_date
