"""
Update as on 10-11-2025: 
    * Removed color comparison
    * Removed easyocr initialization
    * Commented out process_image_for_detections_easyocr
"""

import os
import time
import cv2
import numpy as np
import easyocr
import re
import json
from datetime import datetime
import requests

# ====== GPIO Setup (with optional mock) ======
from gpiozero import LED, Button, Device
from gpiozero.pins.mock import MockFactory  # <-- for simulation

# 🔁 UNCOMMENT THE NEXT LINE FOR TESTING WITHOUT RASPBERRY PI HARDWARE
Device.pin_factory = MockFactory()

# GPIO
led = LED(18)

from threading import Lock
from signal import pause
# ============================================

# ==========================
# Configuration
# ==========================
INCOMING_DIR = "/home/admin/incoming"
PROCESSED_DIR = "/home/admin/incoming/processed"

import cv2
import os
import json
import glob

INCOMING_DIR = "/home/admin/incoming"
REGION_CONFIG_PATH = os.path.join(INCOMING_DIR, "regions.json")

# =====================================================
# Region Selection Logic
# =====================================================

def find_latest_snap(prefix):
    """Find latest snap image for given prefix (snap1_ or snap2_)."""
    pattern = os.path.join(INCOMING_DIR, f"{prefix}_*.png")
    files = glob.glob(pattern)
    if not files:
        print(f"⚠️ No files found for pattern: {pattern}")
        return None
    return max(files, key=os.path.getmtime)

def select_regions_from_latest_snaps():
    """Allow user to manually select OCR regions for snap1_ and snap2_ images."""
    snap1 = find_latest_snap("snap1")
    snap2 = find_latest_snap("snap2")

    if not snap1 or not snap2:
        print("❌ Could not find both snap1_ and snap2_ images.")
        return None, None

    # --- Region 1 selection ---
    print("\n🖱️  Select region for snap1_ (press ENTER or SPACE to confirm)")
    img1 = cv2.imread(snap1)
    if img1 is None:
        print(f"❌ Failed to open {snap1}")
        return None, None
    r1 = cv2.selectROI("Select Region for snap1_", img1)
    cv2.destroyWindow("Select Region for snap1_")

    # --- Region 2 selection ---
    print("\n🖱️  Select region for snap2_ (press ENTER or SPACE to confirm)")
    img2 = cv2.imread(snap2)
    if img2 is None:
        print(f"❌ Failed to open {snap2}")
        return None, None
    r2 = cv2.selectROI("Select Region for snap2_", img2)
    cv2.destroyWindow("Select Region for snap2_")

    return tuple(map(int, r1)), tuple(map(int, r2))

def save_regions(region1, region2):
    data = {
        "REGION_1": region1,
        "REGION_2": region2
    }
    with open(REGION_CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved regions to {REGION_CONFIG_PATH}")

def load_regions():
    if os.path.exists(REGION_CONFIG_PATH):
        with open(REGION_CONFIG_PATH, "r") as f:
            data = json.load(f)
        print(f"✅ Loaded regions from {REGION_CONFIG_PATH}")
        return tuple(data["REGION_1"]), tuple(data["REGION_2"])
    return None, None


# Two OCR regions: (x, y, w, h)
# REGION_1 = (524, 268, 210, 346)   # Button 1
# REGION_2 = (800, 268, 210, 346)   # Button 2 — adjust as needed

# =====================================================
# Load or create OCR regions
# =====================================================
REGION_1, REGION_2 = load_regions()

if not REGION_1 or not REGION_2:
    print("\n⚙️  No saved regions found. Entering region setup mode...")
    REGION_1, REGION_2 = select_regions_from_latest_snaps()
    if REGION_1 and REGION_2:
        save_regions(REGION_1, REGION_2)
    else:
        print("❌ Region selection failed — exiting.")
        exit(1)

print(f"✅ Using REGION_1={REGION_1}, REGION_2={REGION_2}")

BUTTON_1_PIN = 17
BUTTON_2_PIN = 27
TIMEOUT_SECONDS = 15

os.makedirs(PROCESSED_DIR, exist_ok=True)



# OCR Reader (initialized once)
# reader = easyocr.Reader(['en'])

# Global state to track received screenshots
received_screenshots = {
    'button1': None,
    'button2': None
}
#state_lock = Lock()

# ==========================
# Helper Functions
# ==========================
def extract_floats(text):
    return re.findall(r"\d+\.\d+", text)

# ==========================
# Image preprocessing for OCR
# ==========================
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

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    gray_enhanced = clahe.apply(gray_masked)

    thresh = cv2.adaptiveThreshold(gray_masked, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 15, 8)

    kernel = np.ones((2,2), np.uint8)
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

# ==========================
# Core OCR Processing (headless)
# ==========================
# def process_image_for_detections_easyocr(path, region):
#     image = cv2.imread(path)
#     if image is None:
#         print(f"❌ Failed to read image: {path}")
#         return []

#     x, y, w, h = region
#     cropped = image[y:y+h, x:x+w]

#     processed, mask_green, mask_red, mask_yellow = preprocess_for_ocr(cropped, return_masks=True)

#     result = reader.readtext(
#         processed,
#         detail=1,
#         allowlist='0123456789.',
#         contrast_ths=0.1,
#         adjust_contrast=0.5,
#         width_ths=0.1,
#         height_ths=0.1,
#         text_threshold=0.5,
#         low_text=0.3,
#         mag_ratio=1.5,
#         paragraph=False
#     )

#     detections = []
#     overlay = cropped.copy()

#     for (bbox, text, prob) in result:
#         floats = extract_floats(text)
#         if floats:
#             color = get_background_color(cropped, bbox, mask_green, mask_red, mask_yellow)
#             for f in floats:
#                 detections.append({"value": float(f), "color": color})

#             tl = tuple(map(int, bbox[0]))
#             br = tuple(map(int, bbox[2]))
#             cv2.rectangle(overlay, tl, br, (0, 0, 255), 2)
#             cv2.putText(overlay, f"{text} ({color})", (tl[0], tl[1]-5),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

#     base = os.path.splitext(os.path.basename(path))[0]
#     overlay_path = os.path.join(PROCESSED_DIR, f"{base}_overlay.png")
#     cv2.imwrite(overlay_path, overlay)

#     os.rename(path, os.path.join(PROCESSED_DIR, os.path.basename(path)))
#     return detections


from doctr.models import ocr_predictor
from doctr.io import DocumentFile

# Initialize Doctr OCR model globally (once)
doctr_model = ocr_predictor('db_resnet50', 'crnn_vgg16_bn', pretrained=True)

def classify_color(bgr):
    b, g, r = bgr
    if r > 150 and g < 100 and b < 100:
        return "red"
    elif g > 150 and r < 100 and b < 100:
        return "green"
    elif r > 150 and g > 150 and b < 80:
        return "yellow"
    else:
        return "other"

def process_image_for_detections(path, region):
    image = cv2.imread(path)
    if image is None:
        print(f"❌ Failed to read image: {path}")
        return []

    x, y, w, h = region
    cropped = image[y:y+h, x:x+w]

    # Save cropped temporarily (required by doctr)
    temp_path = "/tmp/temp_roi.png"
    cv2.imwrite(temp_path, cropped)

    # Run OCR
    doc = DocumentFile.from_images(temp_path)
    result = doctr_model(doc)
    page = result.pages[0]

    detections = []
    overlay = cropped.copy()
    h, w, _ = cropped.shape
    float_pattern = re.compile(r"\d+\.\d+")

    for block in page.blocks:
        for line in block.lines:
            for word in line.words:
                text = word.value
                matches = float_pattern.findall(text)
                if matches:
                    (x_min, y_min), (x_max, y_max) = word.geometry
                    x1i, y1i = int(x_min * w), int(y_min * h)
                    x2i, y2i = int(x_max * w), int(y_max * h)

                    #region_word = cropped[y1i:y2i, x1i:x2i]

                    # avg_color = cv2.mean(region_word)[:3]
                    # color_name = classify_color(avg_color)

                    for f in matches:
                        detections.append({"value": float(f)})
                        #detections.append(float(f))

                    # Draw overlays for visualization
                    cv2.rectangle(overlay, (x1i, y1i), (x2i, y2i), (0, 0, 255), 2)
                    cv2.putText(
                        overlay, text, (x1i, max(20, y1i - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1
                    )

    # Save overlay and move original file
    base = os.path.splitext(os.path.basename(path))[0]
    overlay_path = os.path.join(PROCESSED_DIR, f"{base}_overlay.png")
    cv2.imwrite(overlay_path, overlay)

    os.rename(path, os.path.join(PROCESSED_DIR, os.path.basename(path)))
    return detections


# ==========================
# Combined Transmission
# ==========================
def combine_and_transmit():
    global received_screenshots

    #with state_lock:
    path1 = received_screenshots['button1']
    path2 = received_screenshots['button2']
    received_screenshots = {'button1': None, 'button2': None}

    if not path1 or not path2:
        print("❌ combine_and_transmit called without both screenshots!")
        return

    print("✅ Both screenshots received. Processing OCR...")

    try:
        detections1 = process_image_for_detections(path1, REGION_1)
        print(detections1)
        detections2 = process_image_for_detections(path2, REGION_2)
        print(detections2)
    except Exception as e:
        print(f"❌ OCR processing failed: {e}")
        return

    all_detections = detections1[:3] + detections2[3:]

    result_data = {
        "filename": f"{os.path.basename(path1)} + {os.path.basename(path2)}",
        "processed_at": datetime.now().isoformat(),
        "detections": all_detections
    }

    print("\n" + "="*60)
    print("📤 Combined OCR Result (JSON):")
    print("="*60)
    print(json.dumps(result_data, indent=2))
    print("="*60)

    #status = "OK" if (all_detections and all(d["color"] == "green" for d in all_detections)) else "NG"
    values = [d["value"] for d in all_detections[:6]]

    ## TRANSIMITTING ONLY VALUES, STATUS WILL BE CALCULATED AT NODE-RED
    # transmit_json = {
    #     "status": status,
    #     "values": values
    # }
    transmit_json = {
        "values" : values
    }

    print("\n📤 Transmit JSON (for HTTP POST):")
    print(json.dumps(transmit_json, indent=2))
    print("="*60)

    try:
        if len(values) == 6:
            print(f" 6 values received. Transmitting to NODE-RED")
            response = requests.post(
            "http://192.168.1.200:1880/gauge2",
            json=transmit_json,
            timeout=5
            )
        if response.status_code == 200:
            print("✅ Successfully sent to Node-RED")
        else:
            print(f"⚠️ Node-RED returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to send to Node-RED: {e}")

# ==========================
# Button Handlers
# ==========================
def handle_button_press(button_id):
    region_name = "Region 1" if button_id == 'button1' else "Region 2"
    prefix_flag = "capture1_" if button_id == 'button1' else "capture2_"
    #prefix_flag = "capture_"
    prefix_snap = "snap1_" if button_id == 'button1' else "snap2_"

    print(f"🟢 {region_name} button pressed! Sending capture request...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    flag_filename = f"{prefix_flag}{timestamp}.flag"
    flag_path = os.path.join(INCOMING_DIR, flag_filename)

    with open(flag_path, 'w') as f:
        f.write(f"Triggered {button_id} at {timestamp}\n")
    print(f"   ➤ Flag created: {flag_filename}")

    start_time = time.time()
    screenshot_path = None

    while time.time() - start_time < TIMEOUT_SECONDS:
        for f in os.listdir(INCOMING_DIR):
            if f.startswith(prefix_snap) and f.endswith('.png'):
                full_path = os.path.join(INCOMING_DIR, f)
                try:
                    if os.path.getctime(full_path) > start_time - 1:
                        screenshot_path = full_path
                        break
                except OSError:
                    continue
        if screenshot_path:
            break
        time.sleep(0.3)

    if os.path.exists(flag_path):
        try:
            os.remove(flag_path)
        except:
            pass

    if screenshot_path:
        print(f"📸 {region_name} screenshot received: {os.path.basename(screenshot_path)}")
        #with state_lock:
        received_screenshots[button_id] = screenshot_path
        if received_screenshots['button1'] and received_screenshots['button2']:
            print("✅ Both buttons pressed. Starting combined OCR.")
            led.on()
            try:
                combine_and_transmit()
            finally:
                led.off()
        else:
            print(f"⏳ Waiting for the other button...")
    else:
        print(f"❌ Timeout ({TIMEOUT_SECONDS}s): No {region_name} screenshot received.")

def on_button1_press():
    led.on()
    time.sleep(0.5)
    led.off()
    handle_button_press('button1')

def on_button2_press():
    led.on()
    time.sleep(0.5)
    led.off()
    handle_button_press('button2')

# ==========================
# Simulate Button Presses (for Mock Testing)
# ==========================
def simulate_button_press(button_num):
    """Simulate hardware button press when using MockFactory."""
    if not isinstance(Device.pin_factory, MockFactory):
        print("⚠️  MockFactory not active. Cannot simulate press.")
        return

    pin_num = BUTTON_1_PIN if button_num == 1 else BUTTON_2_PIN
    pin = Device.pin_factory.pin(pin_num)
    pin.drive_low()   # Press
    time.sleep(0.1)
    pin.drive_high()  # Release
    print(f"⌨️  Simulated Button {button_num} press!")

# ==========================
# Main
# ==========================
def main():
    print("🚀 Starting Dual-Button OCR System")
    print(f"   ➤ Shared folder: {INCOMING_DIR}")
    print(f"   ➤ Button 1 → GPIO {BUTTON_1_PIN}")
    print(f"   ➤ Button 2 → GPIO {BUTTON_2_PIN}")
    print(f"   ➤ Timeout: {TIMEOUT_SECONDS} seconds")

    # Indicate mock mode
    if isinstance(Device.pin_factory, MockFactory):
        print("🧪 MOCK MODE: Using simulated GPIO (no hardware required)")
        print("   ➤ Press '1' or '2' in terminal to simulate button presses.")
    else:
        print("🔌 REAL HARDWARE MODE: Using physical GPIO")

    # Startup blink
    for _ in range(2):
        print("LED: ON")
        led.on()
        time.sleep(0.3)
        print("LED: OFF")
        led.off()
        time.sleep(0.3)

    # Setup buttons
    button1 = Button(BUTTON_1_PIN, pull_up=False, bounce_time=0.1)
    button2 = Button(BUTTON_2_PIN, pull_up=False, bounce_time=0.1)

    button1.when_pressed = on_button1_press
    button2.when_pressed = on_button2_press

    try:
        print("💤 Waiting for button presses... (Press Ctrl+C to quit)")
        if isinstance(Device.pin_factory, MockFactory):
            print("⌨️  In mock mode: type '1', '2', or 'q' below.")
            while True:
                cmd = input("Enter '1', '2', or 'q' to quit: ").strip()
                if cmd == '1':
                    simulate_button_press(1)
                elif cmd == '2':
                    simulate_button_press(2)
                elif cmd == 'q':
                    break
                else:
                    print("Invalid input. Use '1', '2', or 'q'.")
        else:
            pause()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")

if __name__ == "__main__":
    main()
