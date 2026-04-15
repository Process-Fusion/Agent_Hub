import os
import csv
import random
import shutil
from datasets import load_dataset

OUTPUT_DIR = "document_dataset"
IMG_DIR = os.path.join(OUTPUT_DIR, "images")

os.makedirs(IMG_DIR, exist_ok=True)

rows = []

def save_images(dataset, classification, limit=200):
    
    count = 0
    
    for sample in dataset:
        
        if count >= limit:
            break
            
        img = sample["image"]
        filename = f"{classification}_{count}.png"
        path = os.path.join(IMG_DIR, filename)
        
        img.save(path)
        
        rows.append([filename, classification])
        
        count += 1


# 1️⃣ Real receipt dataset
receipt_dataset = load_dataset(
    "Voxel51/scanned_receipts",
    split="train"
)

save_images(receipt_dataset, "receipt", 200)


# 2️⃣ Invoice dataset
invoice_dataset = load_dataset(
    "nielsr/funsd",
    split="train"
)

save_images(invoice_dataset, "invoice", 150)


# 3️⃣ Utility / bill documents
utility_dataset = load_dataset(
    "aharley/rvl_cdip",
    split="train[:150]"
)

save_images(utility_dataset, "utilities", 150)


# Create CSV
csv_path = os.path.join(OUTPUT_DIR, "labels.csv")

with open(csv_path, "w", newline="") as f:
    
    writer = csv.writer(f)
    writer.writerow(["filename", "classification"])
    
    writer.writerows(rows)

print("Dataset created with", len(rows), "images")