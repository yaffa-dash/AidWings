
from datetime import datetime, timezone


def create_assessment_report(
    assessment_id,
    location,
    description,
    category,
    image_analysis
):

    report = {
        "project": "AidWings",

        "assessment_id": assessment_id,

        "report_created": datetime.now(
            timezone.utc
        ).isoformat(),

        "submitted_information": {
            "location": location,
            "description": description,
            "reported_category": category
        },

        "image_analysis": {
            "model": image_analysis.get("model"),
            "predictions": image_analysis.get("predictions", []),
            "analysis_type": "General image classification",
            "verified": False
        },

        "assessment_status": {
            "status": "Pending human review",
            "ai_decision": "No confirmed humanitarian classification",
            "human_review_required": True
        },

        "notice": (
            "AI predictions are preliminary and must not "
            "be treated as confirmed humanitarian findings."
        )
    }

    return report
