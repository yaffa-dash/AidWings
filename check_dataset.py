
from pathlib import Path
import json

# AidWings dataset location
DATASET_DIR = Path("dataset")

# Allowed image formats
IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".webp"}

# Our four humanitarian categories
CATEGORIES = [
    "blocked_access_route",
    "damaged_infrastructure",
    "supply_shortage",
    "other"
]

def check_dataset():

    print("\n========== AIDWINGS DATASET CHECK ==========\n")

    if not DATASET_DIR.exists():
        print("ERROR: Dataset folder not found.")
        return

    total_images = 0

    for category in CATEGORIES:

        category_path = DATASET_DIR / category

        if not category_path.exists():
            print(f"ERROR: Missing folder: {category}")
            continue

        images = [
            file for file in category_path.iterdir()
            if file.is_file() and file.suffix.lower() in IMAGE_FORMATS
        ]

        print(f"{category}: {len(images)} images")

        total_images += len(images)

    print("\n--------------------------------------------")
    print(f"TOTAL IMAGES: {total_images}")

    info_path = DATASET_DIR / "dataset_info.json"

    if info_path.exists():
        with open(info_path, "r", encoding="utf-8") as file:
            info = json.load(file)

        info["images_collected"] = total_images

        with open(info_path, "w", encoding="utf-8") as file:
            json.dump(info, file, indent=4)

        print("Dataset information updated.")

    print("\nDataset check completed!")
    print("============================================\n")


if __name__ == "__main__":
    check_dataset()
