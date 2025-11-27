import xml.etree.ElementTree as ET
import os
import shutil

# --- Configuration ---
# Map object names in the XML to the desired YOLO class ID
CLASS_MAPPING = {
    'frame': 0,  # Panels are represented by <frame> tags
    'text': 1    # Text regions are represented by <text> tags
}

def normalize_box(xmin, ymin, xmax, ymax, img_width, img_height):
    """
    Converts absolute pixel coordinates to normalized YOLO format (x_center, y_center, w, h).
    """
    
    # 1. Calculate pixel dimensions
    pixel_width = xmax - xmin
    pixel_height = ymax - ymin
    
    # 2. Calculate pixel center coordinates
    pixel_x_center = xmin + (pixel_width / 2)
    pixel_y_center = ymin + (pixel_height / 2)
    
    # 3. Normalize coordinates (divide by image dimensions)
    x_center = pixel_x_center / img_width
    y_center = pixel_y_center / img_height
    w = pixel_width / img_width
    h = pixel_height / img_height
    
    # YOLO requires floating-point precision, typically 5-6 decimal places
    return f"{x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}"

def process_manga_xml_and_move_images(xml_file_path, base_image_dir, output_labels_dir, output_images_dir):
    """
    Reads a manga XML, creates label files, and moves the corresponding original 
    image files to the final YOLO directory structure.
    """
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    book_title = root.get('title')

    #Iterate through all pages in the book
    for page_element in root.findall('pages/page'):
        page_index = page_element.get('index')
        img_width = int(page_element.get('width'))
        img_height = int(page_element.get('height'))
        
        # --- 1. Define Consistent File Names ---
        # The common base name ensures both label and image files match.
        base_name = f"book_{book_title}_page_{page_index.zfill(3)}"
        
        # --- 2. Handle Label Creation (from previous script) ---
        label_filename = f"{base_name}.txt"
        label_output_path = os.path.join(output_labels_dir, label_filename)
        yolo_lines = []
        
        # --- B. Process Annotations ---
        
        # 1. Extract and convert <frame> annotations (Panels)
        for frame in page_element.findall('frame'):
            class_id = CLASS_MAPPING['frame']  # 0
            
            # Extract absolute coordinates
            xmin = int(frame.get('xmin'))
            ymin = int(frame.get('ymin'))
            xmax = int(frame.get('xmax'))
            ymax = int(frame.get('ymax'))
            
            # Convert to normalized YOLO format
            normalized_coords = normalize_box(xmin, ymin, xmax, ymax, img_width, img_height)
            
            yolo_lines.append(f"{class_id} {normalized_coords}")
            
        # 2. Extract and convert <text> annotations (Text)
        for text in page_element.findall('text'):
            class_id = CLASS_MAPPING['text']  # 1
            
            # Extract absolute coordinates
            xmin = int(text.get('xmin'))
            ymin = int(text.get('ymin'))
            xmax = int(text.get('xmax'))
            ymax = int(text.get('ymax'))
            
            # Convert to normalized YOLO format
            normalized_coords = normalize_box(xmin, ymin, xmax, ymax, img_width, img_height)
            
            yolo_lines.append(f"{class_id} {normalized_coords}")
            
        # --- C. Write Output File ---
        # Write the label file
            if yolo_lines:
                with open(label_output_path, 'w') as f:
                    f.write('\n'.join(yolo_lines))
                print(f"Created label file: {label_output_path}")

            original_image_filename = f"{int(page_index):03d}.jpg"
            original_image_path = os.path.join(base_image_dir, book_title, original_image_filename)
            
            # Set the target path with the new, consistent file name

            target_image_filename = f"{base_name}.jpg"
            target_image_path = os.path.join(output_images_dir, target_image_filename)
            
            if os.path.exists(original_image_path):
                # Use shutil.copy to copy the image without deleting the original
                # Use shutil.move if you want to move (cut) the file
                shutil.copy(original_image_path, target_image_path)
                print(f"Copied image: {target_image_path}")
            else:
                print(f"ERROR: Image not found at {original_image_path}")

# 1. Define all necessary paths
BASE_XML_DIR = 'Manga109s/annotations/'
ORIGINAL_IMAGES_DIR = 'Manga109s/images/'

FINAL_YOLO_TRAIN_LABELS = 'manga109s-dataset/labels/train/'
FINAL_YOLO_TRAIN_IMAGES = 'manga109s-dataset/images/train/'

FINAL_YOLO_VAL_LABELS = 'manga109s-dataset/labels/val/'
FINAL_YOLO_VAL_IMAGES = 'manga109s-dataset/images/val/'

# 2. Loop through all XML files

xml_files = sorted([f for f in os.listdir(BASE_XML_DIR) if f.endswith(".xml")])

# 80/20 split
split_idx = int(len(xml_files) * 0.8)
train_xmls = xml_files[:split_idx]
val_xmls = xml_files[split_idx:]

print("Train:", len(train_xmls))
print("Val:", len(val_xmls))

for xml_file in train_xmls:
    xml_path = os.path.join(BASE_XML_DIR, xml_file)
    process_manga_xml_and_move_images(
        xml_path,
        ORIGINAL_IMAGES_DIR,
        FINAL_YOLO_TRAIN_LABELS,
        FINAL_YOLO_TRAIN_IMAGES
    )

for xml_file in val_xmls:
    xml_path = os.path.join(BASE_XML_DIR, xml_file)
    process_manga_xml_and_move_images(
        xml_path,
        ORIGINAL_IMAGES_DIR,
        FINAL_YOLO_VAL_LABELS,   # <-- Make sure you have a VAL folder
        FINAL_YOLO_VAL_IMAGES
    )

print("Done.")
