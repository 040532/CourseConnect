import csv
import json
import re
from pathlib import Path
import sys
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from sqlalchemy import delete

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.config import CATALOG_INDEX_URL, CATALOG_ROOT_URL, COURSES_CSV_PATH, COURSES_JSON_PATH, PROCESSED_DIR
from backend.app.db import Base, SessionLocal, engine
from backend.app.models import Course


HEADERS = {
    "User-Agent": "CourseConnectBot/1.0 (+https://catalog.tamu.edu/graduate/course-descriptions/)"
}
SUBJECT_PATH_PATTERN = re.compile(r"^/graduate/course-descriptions/[a-z0-9-]+/?$", re.IGNORECASE)
TITLE_PATTERN = re.compile(
    r"^(?P<code>[A-Z]{2,5}\s*\d{3}(?:/[A-Z]{2,5}\s*\d{3})?)\s+(?P<title>.+?)(?:\.\s*)?$"
)


def ensure_directories() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def discover_subject_links(index_html: str) -> list[str]:
    soup = BeautifulSoup(index_html, "html.parser")
    links: set[str] = set()
    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "").strip()
        if not href or href.endswith("/graduate/course-descriptions/"):
            continue
        if SUBJECT_PATH_PATTERN.match(href):
            links.add(urljoin(CATALOG_ROOT_URL, href))
    return sorted(links)


def split_title_line(title_line: str) -> tuple[str, str]:
    clean_title = normalize_whitespace(title_line).replace("\xa0", " ")
    match = TITLE_PATTERN.match(clean_title)
    if match:
        return normalize_whitespace(match.group("code")), normalize_whitespace(match.group("title"))

    prefix_match = re.match(r"^([A-Z]{2,5}\s*\d{3}(?:/[A-Z]{2,5}\s*\d{3})?)\s+", clean_title)
    if prefix_match:
        code = normalize_whitespace(prefix_match.group(1))
        return code, normalize_whitespace(clean_title[prefix_match.end() :].rstrip("."))
    return "", clean_title


def extract_prerequisites(text: str) -> str:
    match = re.search(r"Prerequisites?:\s*(.+?)(?=(Cross Listing:|Restrictions:|$))", text, re.IGNORECASE)
    return normalize_whitespace(match.group(1)) if match else ""


def extract_credits(text: str) -> str:
    match = re.search(r"Credits?\s+([^.]+)\.", text, re.IGNORECASE)
    return normalize_whitespace(match.group(1)) if match else ""


def extract_description(text: str) -> str:
    normalized = normalize_whitespace(text)
    normalized = re.sub(r"^Credits?\s+[^.]+\.\s*", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"Prerequisites?:\s*.+$", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"Cross Listing:\s*.+$", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"Restrictions?:\s*.+$", "", normalized, flags=re.IGNORECASE)
    return normalize_whitespace(normalized.rstrip(". ")) + "."


def parse_course_blocks(subject_html: str) -> Iterable[dict]:
    soup = BeautifulSoup(subject_html, "html.parser")
    for block in soup.select(".courseblock"):
        title_element = block.select_one(".courseblocktitle")
        description_element = block.select_one(".courseblockdesc")
        if not title_element or not description_element:
            continue

        code, title = split_title_line(title_element.get_text(" ", strip=True))
        if not code or not title:
            continue
        if "special topics in" in title.lower():
            continue

        description_text = description_element.get_text(" ", strip=True)
        extra_text = block.select_one(".courseblockextra")
        full_text = " ".join(
            part for part in [description_text, extra_text.get_text(" ", strip=True) if extra_text else ""] if part
        )

        course = {
            "code": code,
            "title": title,
            "credits": extract_credits(description_text),
            "description": extract_description(full_text),
            "prerequisites": extract_prerequisites(full_text),
        }
        if course["description"] and course["description"] != ".":
            yield course


def write_json(records: list[dict]) -> None:
    COURSES_JSON_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=True), encoding="utf-8")


def write_csv(records: list[dict]) -> None:
    with COURSES_CSV_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["code", "title", "credits", "description", "prerequisites"])
        writer.writeheader()
        writer.writerows(records)


def write_database(records: list[dict]) -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        session.execute(delete(Course))
        session.bulk_insert_mappings(Course, records)
        session.commit()


def main() -> None:
    ensure_directories()
    index_html = fetch_html(CATALOG_INDEX_URL)
    subject_links = discover_subject_links(index_html)

    records_by_code: dict[str, dict] = {}
    for subject_link in subject_links:
        subject_html = fetch_html(subject_link)
        for course in parse_course_blocks(subject_html):
            records_by_code[course["code"]] = course

    records = sorted(records_by_code.values(), key=lambda item: item["code"])
    write_json(records)
    write_csv(records)
    write_database(records)

    print(f"Scraped {len(records)} graduate courses.")
    print(f"JSON saved to {COURSES_JSON_PATH}")
    print(f"CSV saved to {COURSES_CSV_PATH}")


if __name__ == "__main__":
    main()
