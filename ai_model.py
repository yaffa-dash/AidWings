
image_classifier = None


def analyze_image(image_path):
    global image_classifier

    if image_classifier is None:
        from transformers import pipeline

        print("Loading AidWings image model...")
        image_classifier = pipeline(
            task="image-classification",
            model="google/vit-base-patch16-224"
        )
        print("AidWings image model loaded successfully!")

    results = image_classifier(image_path)

    return {
        "model": "Google ViT",
        "predictions": [
            {
                "label": result["label"],
                "confidence": round(result["score"], 4)
            }
            for result in results[:5]
        ],
        "human_review_required": True
    }
