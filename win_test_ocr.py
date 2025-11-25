import os
import re
import cv2
import numpy as np
import easyocr

# ======================
# Configuration
# ======================
IMAGE_PATH = "snap2_current.png"   # 👈 Change this
PROCESSED_DIR = "processed"

os.makedirs(PROCESSED_DIR, exist_ok=True)

# Initialize EasyOCR
reader = easyocr.Reader(['en'])


# ======================
# Utility Functions
# ======================
def extract_floats(text):
    """Extract floating-point numbers from detected text."""
    return re.findall(r"\d+\.\d+|\d+", text)


def preprocess_for_ocr(cropped, return_masks=False):
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(cropped, cv2.COLOR_BGR2HSV)

    lower_green = np.array([40, 40, 40])
    upper_green = np.array([80, 255, 255])
    mask_green = cv2.inRange(hsv, lower_green, upper_green)

    lower_red1 = np.array([0, 40, 40])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 40, 40])
    upper_red2 = np.array([180, 255, 255])
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = cv2.bitwise_or(mask_red1, mask_red2)

    lower_yellow = np.array([20, 40, 40])
    upper_yellow = np.array([40, 255, 255])
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)

    mask_background = cv2.bitwise_or(cv2.bitwise_or(mask_green, mask_red), mask_yellow)
    _, mask_dark = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
    mask_text = cv2.bitwise_and(mask_dark, cv2.bitwise_not(mask_background))

    gray_masked = gray.copy()
    gray_masked[mask_text == 0] = 255

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray_enhanced = clahe.apply(gray_masked)

    thresh = cv2.adaptiveThreshold(
        gray_masked, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 15, 8
    )

    kernel = np.ones((2, 2), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    if return_masks:
        return thresh, mask_green, mask_red, mask_yellow
    else:
        return thresh


def get_background_color(original_crop, bbox, mask_green, mask_red, mask_yellow):
    pts = np.array(bbox, dtype=np.int32)
    mask_roi = np.zeros(original_crop.shape[:2], dtype=np.uint8)
    cv2.fillConvexPoly(mask_roi, pts, 255)

    green_overlap = cv2.countNonZero(cv2.bitwise_and(mask_roi, mask_green))
    red_overlap = cv2.countNonZero(cv2.bitwise_and(mask_roi, mask_red))
    yellow_overlap = cv2.countNonZero(cv2.bitwise_and(mask_roi, mask_yellow))

    total = green_overlap + red_overlap + yellow_overlap
    if total == 0:
        return "unknown"

    if green_overlap >= red_overlap and green_overlap >= yellow_overlap:
        return "green"
    elif red_overlap >= yellow_overlap:
        return "red"
    else:
        return "yellow"


# ======================
# Core OCR Processing
# ======================
def process_image_for_detections(path, region):
    image = cv2.imread(path)
    if image is None:
        print(f"❌ Failed to read image: {path}")
        return []

    x, y, w, h = region
    cropped = image[y:y+h, x:x+w]

    processed, mask_green, mask_red, mask_yellow = preprocess_for_ocr(cropped, return_masks=True)

    result = reader.readtext(
        processed,
        detail=1,
        allowlist='0123456789.',
        contrast_ths=0.1,
        adjust_contrast=0.5,
        width_ths=0.1,
        height_ths=0.1,
        text_threshold=0.5,
        low_text=0.3,
        mag_ratio=1.5,
        paragraph=False
    )

    detections = []
    overlay = cropped.copy()

    for (bbox, text, prob) in result:
        floats = extract_floats(text)
        if floats:
            color = get_background_color(cropped, bbox, mask_green, mask_red, mask_yellow)
            for f in floats:
                detections.append({"value": float(f), "color": color})

            tl = tuple(map(int, bbox[0]))
            br = tuple(map(int, bbox[2]))
            cv2.rectangle(overlay, tl, br, (0, 0, 255), 2)
            cv2.putText(overlay, f"{text} ({color})", (tl[0], tl[1]-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    base = os.path.splitext(os.path.basename(path))[0]
    overlay_path = os.path.join(PROCESSED_DIR, f"{base}_overlay.png")
    cv2.imwrite(overlay_path, overlay)

    print(f"✅ Saved overlay image: {overlay_path}")
    os.rename(path, os.path.join(PROCESSED_DIR, os.path.basename(path)))
    return detections


# ======================
# Manual ROI Selection
# ======================
def select_region(image_path):
    image = cv2.imread(image_path)
    if image is None:
        print("❌ Could not load image.")
        return None

    print("📸 Select the ROI (drag with mouse, press ENTER or SPACE to confirm, ESC to cancel)")
    r = cv2.selectROI("Select Region", image, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    x, y, w, h = map(int, r)
    if w == 0 or h == 0:
        print("⚠️ No region selected.")
        return None
    else:
        print(f"✅ Selected region: x={x}, y={y}, w={w}, h={h}")
        return (x, y, w, h)


# ======================
# Run the Script
# ======================
if __name__ == "__main__":
    region = select_region(IMAGE_PATH)
    if region:
        detections = process_image_for_detections(IMAGE_PATH, region)
        print("\n📄 OCR Detections:")
        for d in detections:
            print(f"  ➤ {d['value']} ({d['color']})")
