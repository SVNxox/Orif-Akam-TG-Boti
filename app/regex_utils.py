import re

PATTERN = re.compile(r"\d+")

def extract_numbers(text: str) -> str:
    if not text:
        return ""

    match = PATTERN.search(text)

    return match.group() if match else ""
