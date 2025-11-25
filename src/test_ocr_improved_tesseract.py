import os
import time
import cv2
import numpy as np
import pytesseract
import re
from datetime import datetime

INCOMING_DIR = "/home/admin/incoming"
PROCESSED_DIR = "/home/admin/incoming/processed"

# Default region (x, y, w, h)
REGION = (100, 200, 400, 300)

os.makedirs(PROCESSED_DIR, exist_ok=True)

def extract_floats(text):
    """Extract floating point numbers from text"""
    # Remove whitespace and newlines
    text = text.replace(' ', '').replace('\n', '')
    
    # Find decimal numbers
    matches = re.findall(r"\d+\.\d+", text)
    return matches

# ==========================
# Interactive region selector
# ==========================
ref_point = []
cropping = False
temp_image = None

def click_and_crop(event, x, y, flags, param):
    global ref_point, cropping, temp_image
    if event == cv2.EVENT_LBUTTONDOWN:
        ref_point = [(x, y)]
        cropping = True
    elif event == cv2.EVENT_LBUTTONUP:
        ref_point.append((x, y))
        cropping = False
        cv2.rectangle(temp_image, ref_point[0], ref_point[1], (0, 255, 0), 2)
        cv2.imshow("Select Region", temp_image)
        print(f"Selected region: {ref_point}")

def select_region(image):
    global temp_image
    temp_image = image.copy()
    cv2.namedWindow("Select Region")
    cv2.setMouseCallback("Select Region", click_and_crop)
    print("💡 Click and drag to select OCR region, press 'q' to confirm.")

    while True:
        cv2.imshow("Select Region", temp_image)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            temp_image = image.copy()
            ref_point.clear()

    cv2.destroyWindow("Select Region")

    if len(ref_point) == 2:
        x1, y1 = ref_point[0]
        x2, y2 = ref_point[1]
        return (x1, y1, x2-x1, y2-y1)
    return None

# ==========================
# Color-based detection and extraction
# ==========================
def create_color_masks(image):
    """
    Create separate masks for green, yellow, and red backgrounds.
    Returns individual masks and combined mask.
    """
    # Convert to HSV for better color segmentation
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # GREEN range - adjusted based on your sample
    # Your green is quite bright and saturated
    lower_green = np.array([40, 100, 100])
    upper_green = np.array([80, 255, 255])
    
    # YELLOW range - adjusted for your specific yellow
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([35, 255, 255])
    
    # RED range (red wraps around in HSV, so we need two ranges)
    # Lower red (0-10 degrees)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    # Upper red (160-180 degrees)
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    
    # Create individual masks
    mask_green = cv2.inRange(hsv, lower_green, upper_green)
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = cv2.bitwise_or(mask_red1, mask_red2)
    
    # Combine all masks
    combined_mask = cv2.bitwise_or(mask_green, mask_yellow)
    combined_mask = cv2.bitwise_or(combined_mask, mask_red)
    
    # Clean up masks with morphological operations
    kernel = np.ones((5, 5), np.uint8)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    
    return combined_mask, mask_green, mask_yellow, mask_red

def find_value_boxes(mask):
    """
    Find colored value boxes and sort them top to bottom
    """
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    boxes = []
    for contour in contours:
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(contour)
        
        # Filter based on expected size of value boxes
        # Adjust these thresholds based on your image resolution
        if 50 < w < 250 and 15 < h < 70:
            area = cv2.contourArea(contour)
            if area > 500:  # Minimum area threshold
                boxes.append({
                    'bbox': (x, y, w, h),
                    'center_y': y + h // 2,
                    'area': area
                })
    
    # Sort by vertical position (top to bottom)
    boxes.sort(key=lambda b: b['center_y'])
    
    return boxes

def preprocess_box_for_ocr(image, box):
    """
    Preprocess individual colored box for optimal OCR
    Uses approach similar to your working code
    """
    x, y, w, h = box['bbox']
    
    # Add padding
    padding = 5
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(image.shape[1] - x, w + 2 * padding)
    h = min(image.shape[0] - y, h + 2 * padding)
    
    # Extract ROI
    roi = image[y:y+h, x:x+w]
    
    # Convert to grayscale
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Apply bilateral filter to reduce noise while keeping edges sharp
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Use adaptive thresholding for better results
    # This separates black text from colored background
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )
    
    # Invert if needed (text should be black on white for Tesseract)
    if np.mean(thresh) < 127:
        thresh = cv2.bitwise_not(thresh)
    
    # Additional cleanup: remove small noise
    kernel = np.ones((2, 2), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Slightly dilate to make characters more solid
    kernel_dilate = np.ones((1, 1), np.uint8)
    thresh = cv2.dilate(thresh, kernel_dilate, iterations=1)
    
    return thresh, roi

def extract_value_with_tesseract(preprocessed_image):
    """
    Extract numerical value using Tesseract OCR
    """
    # Tesseract configuration optimized for numbers
    # --psm 7: Treat image as single text line
    # --oem 3: Use both legacy and LSTM OCR engines
    custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.'
    
    # Run Tesseract
    text = pytesseract.image_to_string(preprocessed_image, config=custom_config)
    text = text.strip()
    
    # Extract floating point numbers
    floats = extract_floats(text)
    
    # Return the first valid float found
    if floats:
        try:
            float_val = float(floats[0])
            # Validate reasonable range (adjust as needed)
            if 0 < float_val < 100:
                return floats[0], text
        except ValueError:
            pass
    
    return None, text

def get_box_color(image, box, mask_green, mask_yellow, mask_red):
    """
    Determine the color of a box (green, yellow, or red)
    """
    x, y, w, h = box['bbox']
    
    # Check which color mask has more pixels in this box region
    box_region_green = mask_green[y:y+h, x:x+w]
    box_region_yellow = mask_yellow[y:y+h, x:x+w]
    box_region_red = mask_red[y:y+h, x:x+w]
    
    green_pixels = np.sum(box_region_green > 0)
    yellow_pixels = np.sum(box_region_yellow > 0)
    red_pixels = np.sum(box_region_red > 0)
    
    # Return the dominant color
    max_pixels = max(green_pixels, yellow_pixels, red_pixels)
    if max_pixels == green_pixels:
        return 'green', (0, 255, 0)
    elif max_pixels == yellow_pixels:
        return 'yellow', (0, 255, 255)
    else:
        return 'red', (0, 0, 255)

# ==========================
# Image processing
# ==========================
def process_image(path):
    global REGION
    image = cv2.imread(path)
    if image is None:
        print(f"Failed to read: {path}")
        return

    # Show current region on image
    preview = image.copy()
    x, y, w, h = REGION
    cv2.rectangle(preview, (x, y), (x+w, y+h), (0, 255, 0), 2)
    cv2.imshow("Preview Region", preview)
    cv2.waitKey(500)
    cv2.destroyWindow("Preview Region")

    # Ask if user wants to adjust region interactively
    adjust = input("Do you want to adjust OCR region? (y/n): ").lower()
    if adjust == 'y':
        new_region = select_region(image)
        if new_region:
            REGION = new_region
            print(f"✅ Updated OCR region: {REGION}")

    x, y, w, h = REGION
    cropped = image[y:y+h, x:x+w]

    # Prepare base filename for saving intermediate images
    base_name = os.path.splitext(os.path.basename(path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Step 1: Save cropped region
    cropped_path = os.path.join(PROCESSED_DIR, f"{base_name}_1_cropped.png")
    cv2.imwrite(cropped_path, cropped)
    
    # Step 2: Create color masks
    combined_mask, mask_green, mask_yellow, mask_red = create_color_masks(cropped)
    
    # Save individual color masks
    mask_green_path = os.path.join(PROCESSED_DIR, f"{base_name}_2a_mask_green.png")
    mask_yellow_path = os.path.join(PROCESSED_DIR, f"{base_name}_2b_mask_yellow.png")
    mask_red_path = os.path.join(PROCESSED_DIR, f"{base_name}_2c_mask_red.png")
    combined_mask_path = os.path.join(PROCESSED_DIR, f"{base_name}_2d_mask_combined.png")
    
    cv2.imwrite(mask_green_path, mask_green)
    cv2.imwrite(mask_yellow_path, mask_yellow)
    cv2.imwrite(mask_red_path, mask_red)
    cv2.imwrite(combined_mask_path, combined_mask)
    
    # Step 3: Find value boxes
    boxes = find_value_boxes(combined_mask)
    print(f"\n🔍 Found {len(boxes)} value boxes")
    
    # Step 4: Extract values from each box
    results = []
    overlay = cropped.copy()
    
    # Create a canvas to show all preprocessed boxes
    preprocessed_boxes = []
    
    for i, box in enumerate(boxes):
        # Preprocess the box
        preprocessed, roi = preprocess_box_for_ocr(cropped, box)
        preprocessed_boxes.append(preprocessed)
        
        # Extract value using Tesseract
        value, raw_text = extract_value_with_tesseract(preprocessed)
        
        # Get box color
        color_name, color_bgr = get_box_color(cropped, box, mask_green, mask_yellow, mask_red)
        
        # Store result
        result = {
            'index': i + 1,
            'value': value,
            'raw_ocr': raw_text,
            'color': color_name,
            'bbox': box['bbox']
        }
        results.append(result)
        
        # Draw on overlay
        x, y, w, h = box['bbox']
        cv2.rectangle(overlay, (x, y), (x+w, y+h), color_bgr, 2)
        
        if value:
            label = f"#{i+1}: {value}"
            print(f"✅ Box {i+1} ({color_name}): {value}")
        else:
            label = f"#{i+1}: FAILED"
            print(f"❌ Box {i+1} ({color_name}): Failed (raw: '{raw_text}')")
        
        # Add label above box
        cv2.putText(overlay, label, (x, y-5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_bgr, 2)
    
    # Step 5: Save preprocessed boxes side by side
    if preprocessed_boxes:
        # Stack preprocessed boxes vertically with labels
        max_width = max([img.shape[1] for img in preprocessed_boxes])
        labeled_boxes = []
        
        for i, box_img in enumerate(preprocessed_boxes):
            # Create labeled version
            label_height = 30
            labeled = np.ones((box_img.shape[0] + label_height, max_width), dtype=np.uint8) * 255
            
            # Add label
            result = results[i]
            label_text = f"Box {i+1} ({result['color']}): {result['value'] or 'FAIL'}"
            cv2.putText(labeled, label_text, (5, 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, 0, 1)
            
            # Add preprocessed image
            labeled[label_height:, :box_img.shape[1]] = box_img
            labeled_boxes.append(labeled)
        
        # Stack all boxes
        all_boxes = np.vstack(labeled_boxes)
        preprocessed_path = os.path.join(PROCESSED_DIR, f"{base_name}_3_preprocessed_boxes.png")
        cv2.imwrite(preprocessed_path, all_boxes)
    
    # Step 6: Save masked original (colored regions only)
    masked_original = cv2.bitwise_and(cropped, cropped, mask=combined_mask)
    masked_original_path = os.path.join(PROCESSED_DIR, f"{base_name}_4_masked_original.png")
    cv2.imwrite(masked_original_path, masked_original)
    
    # Step 7: Save final overlay
    overlay_path = os.path.join(PROCESSED_DIR, f"{base_name}_5_overlay.png")
    cv2.imwrite(overlay_path, overlay)
    
    # Step 8: Create debug comparison view
    debug_view = np.hstack([
        cv2.cvtColor(combined_mask, cv2.COLOR_GRAY2BGR),
        overlay
    ])
    debug_comparison_path = os.path.join(PROCESSED_DIR, f"{base_name}_6_debug_comparison.png")
    cv2.imwrite(debug_comparison_path, debug_view)
    
    # Step 9: Save results to text file
    results_path = os.path.join(PROCESSED_DIR, f"{base_name}_results.txt")
    with open(results_path, 'w') as f:
        f.write(f"OCR Results - {timestamp}\n")
        f.write("=" * 60 + "\n\n")
        
        successful = sum(1 for r in results if r['value'])
        f.write(f"Successfully extracted: {successful}/{len(results)} values\n\n")
        
        for result in results:
            f.write(f"Box {result['index']} ({result['color']}):\n")
            f.write(f"  Value: {result['value'] or 'FAILED'}\n")
            f.write(f"  Raw OCR: '{result['raw_ocr']}'\n")
            f.write(f"  Position: {result['bbox']}\n\n")
    
    # Print summary
    print(f"\n📸 Processed: {os.path.basename(path)}")
    print(f"✅ Successfully extracted: {successful}/{len(results)} values")
    print("\nExtracted values:")
    for result in results:
        if result['value']:
            print(f"  Box {result['index']} ({result['color']}): {result['value']}")
    
    print(f"\n💾 Saved intermediate images:")
    print(f"   1. Cropped region")
    print(f"   2. Color masks (green, yellow, red, combined)")
    print(f"   3. Preprocessed boxes")
    print(f"   4. Masked original")
    print(f"   5. OCR overlay")
    print(f"   6. Debug comparison")
    print(f"   7. Results text file")

    # Show overlay preview
    cv2.imshow("OCR Results", overlay)
    cv2.waitKey(2000)
    cv2.destroyAllWindows()

    # Move original file to processed directory
    os.rename(path, os.path.join(PROCESSED_DIR, os.path.basename(path)))

# ==========================
# Watch folder
# ==========================
def watch_folder():
    print("🔍 Watching folder for new screenshots...")
    print(f"Directory: {INCOMING_DIR}")
    print(f"Results will be saved to: {PROCESSED_DIR}\n")
    seen = set()

    while True:
        for f in os.listdir(INCOMING_DIR):
            if f.endswith(".png") and f not in seen:
                path = os.path.join(INCOMING_DIR, f)
                print(f"\n{'='*60}")
                print(f"New image detected: {f}")
                print('='*60)
                process_image(path)
                seen.add(f)
        time.sleep(2)

if __name__ == "__main__":
    watch_folder()
