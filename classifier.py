"""AI email classification using Hugging Face zero-shot model."""

from transformers import pipeline

# Load the zero-shot classification model once at import time
print("Loading AI classifier model (facebook/bart-large-mnli)...")
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
print("AI classifier model loaded.")

# Candidate labels for zero-shot classification
CLASSIFICATION_LABELS = [
    "important email",
    "newsletter",
    "spam",
    "job opportunity",
]


def ai_classify_email(subject, snippet):
    """Classify an email using Hugging Face zero-shot classification.

    Combines the subject and snippet into a single text string and
    runs it through facebook/bart-large-mnli to determine the most
    likely category.

    Args:
        subject: The Subject header value.
        snippet: Gmail's short preview text of the email body.

    Returns:
        str: The highest-scoring label from CLASSIFICATION_LABELS.
    """

    # Combine subject and snippet into one text for classification
    text = f"{subject}. {snippet}"

    result = classifier(text, CLASSIFICATION_LABELS)

    # Return the label with the highest confidence score
    return result["labels"][0]
