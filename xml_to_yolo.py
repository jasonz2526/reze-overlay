import os
import xml.etree.ElementTree as ET

XML_DIR = "Manga109s/annotations"
IMG_DIR = "Manga109s/images"
OUT_LABELS = "dataset/labels_manga109"
os.makedirs(OUT_LABELS, exist_ok=True)

# text class = 0
CLASS_ID = 0

for xml_file in os.listdir(XML_DIR):
    if not xml_file.endswith(".xml"):
        continue

    xml_path = os.path.join(XML_DIR, xml_file)
    tree = ET.parse(xml_path)
    root = tree.getroot()

    book_title = root.attrib["title"]

    for page in root.find("pages").findall("page"):
        idx = page.attrib["index"]
        width = float(page.attrib["width"])
        height = float(page.attrib["height"])

        image_name = f"{int(idx):03d}.jpg"
        image_path = os.path.join(IMG_DIR, book_title, image_name)

        if not os.path.exists(image_path):
            print("Image not found:", image_path)
            continue

        # Output label path
        label_path = os.path.join(OUT_LABELS, image_name.replace(".jpg", ".txt"))

        with open(label_path, "w") as out:
            # Loop through all text annotations
            for text in page.findall("text"):
                xmin = float(text.attrib["xmin"])
                ymin = float(text.attrib["ymin"])
                xmax = float(text.attrib["xmax"])
                ymax = float(text.attrib["ymax"])

                xc = (xmin + xmax) / 2 / width
                yc = (ymin + ymax) / 2 / height
                w = (xmax - xmin) / width
                h = (ymax - ymin) / height

                out.write(f"{CLASS_ID} {xc} {yc} {w} {h}\n")

print("Conversion complete!")
