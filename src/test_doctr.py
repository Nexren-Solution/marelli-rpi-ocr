import cv2
import numpy as np
import re
from doctr.models import ocr_predictor
from doctr.io import DocumentFile

# Load Doctr OCR model
ocr_model = ocr_predictor('db_resnet50', 'crnn_vgg16_bn', pretrained=True)

# Path to your image
IMAGE_PATH = "snap1_current2.png"

# Load image
image = cv2.imread(IMAGE_PATH)
clone = image.copy()
roi = []

def select_region(event, x, y, flags, param):
    global roi
    if event == cv2.EVENT_LBUTTONDOWN:
        roi = [(x, y)]
    elif event == cv2.EVENT_LBUTTONUP:
        roi.append((x, y))
        cv2.rectangle(image, roi[0], roi[1], (0, 255, 0), 2)
        cv2.imshow("Select ROI and press 'c' to confirm", image)

cv2.namedWindow("Select ROI and press 'c' to confirm")
cv2.setMouseCallback("Select ROI and press 'c' to confirm", select_region)

while True:
    cv2.imshow("Select ROI and press 'c' to confirm", image)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('c') and len(roi) == 2:
        print(roi)
        (x1, y1), (x2, y2) = roi
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)

        print(x, y, w, h)

        break
    elif key == ord('r'):
        image = clone.copy()
        roi = []
    elif key == 27:  # ESC
        cv2.destroyAllWindows()
        exit()

cv2.destroyAllWindows()

# Crop ROI
x1, y1 = roi[0]
x2, y2 = roi[1]
cropped = clone[min(y1, y2):max(y1, y2), min(x1, x2):max(x1, x2)]

# Run OCR on cropped region
temp_path = "/tmp/temp_roi.png"
cv2.imwrite(temp_path, cropped)
doc = DocumentFile.from_images(temp_path)
result = ocr_model(doc)
page = result.pages[0]

# Function to classify color from average RGB
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

float_pattern = re.compile(r"\d+\.\d+")
output = []

for block in page.blocks:
    for line in block.lines:
        for word in line.words:
            text = word.value
            matches = float_pattern.findall(text)
            if matches:
                # Compute bounding box for color detection
                (x_min, y_min), (x_max, y_max) = word.geometry
                h, w, _ = cropped.shape
                x1i, y1i = int(x_min * w), int(y_min * h)
                x2i, y2i = int(x_max * w), int(y_max * h)

                # Extract region and find average color
                region = cropped[y1i:y2i, x1i:x2i]
                avg_color = cv2.mean(region)[:3]
                color_name = classify_color(avg_color)

                output.append((matches[0], color_name))

print("\n--- Detected Floating Values with Colors ---")
for val, color in output:
    print(f"{val} : {color}")

cv2.imshow("Selected Region", cropped)
cv2.waitKey(0)
cv2.destroyAllWindows()
