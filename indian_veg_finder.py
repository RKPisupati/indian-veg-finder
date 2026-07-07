#!/usr/bin/env python3
"""
Indian Vegetarian Restaurant Finder
------------------------------------
Enter a ZIP code, city, or address and get a list of nearby Indian
vegetarian restaurants (pulled directly from Google Places, not guessed
by an LLM), plus an optional AI-generated summary/recommendation.

Env vars required:
    GEMINI_API_KEY
    GOOGLE_MAPS_API_KEY
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import requests
from google import genai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("indian_veg_finder")

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
        "places.primaryType",
        "places.types",
        "places.googleMapsUri",
        "places.websiteUri",
        "places.nationalPhoneNumber",
        "places.servesVegetarianFood",
        "places.currentOpeningHours.openNow",
        "nextPageToken",
    ]
)

MAX_PAGES = 3          # Places Text Search caps at 20 results/page, 3 pages = up to 60
PAGE_FETCH_DELAY = 2.0  # Google requires a short delay before a next_page_token is valid
REQUEST_TIMEOUT = 15


@dataclass
class Restaurant:
    name: str
    address: str
    rating: Optional[float]
    rating_count: Optional[int]
    price_level: Optional[str]
    maps_url: Optional[str]
    website: Optional[str]
    phone: Optional[str]
    open_now: Optional[bool]
    serves_vegetarian: Optional[bool]
    types: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, p: dict) -> "Restaurant":
        return cls(
            name=p.get("displayName", {}).get("text", "Unknown"),
            address=p.get("formattedAddress", "N/A"),
            rating=p.get("rating"),
            rating_count=p.get("userRatingCount"),
            price_level=p.get("priceLevel"),
            maps_url=p.get("googleMapsUri"),
            website=p.get("websiteUri"),
            phone=p.get("nationalPhoneNumber"),
            open_now=p.get("currentOpeningHours", {}).get("openNow"),
            serves_vegetarian=p.get("servesVegetarianFood"),
            types=p.get("types", []),
        )

    def to_dict(self) -> dict:
        return self.__dict__


class RestaurantFinderError(Exception):
    pass


class IndianVegRestaurantFinder:
    def __init__(self, gemini_api_key: str, maps_api_key: str):
        self.maps_api_key = maps_api_key
        self.client = genai.Client(api_key=gemini_api_key)
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # Location -> lat/lng  (accepts ZIP code, city, or full address)
    # ------------------------------------------------------------------
    def geocode(self, location: str) -> tuple[float, float, str]:
        log.info("Geocoding location: %s", location)
        params = {"address": location, "key": self.maps_api_key}
        resp = self.session.get(GEOCODE_URL, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            raise RestaurantFinderError(
                f"Could not resolve location '{location}': {data.get('status')}"
            )

        result = data["results"][0]
        loc = result["geometry"]["location"]
        formatted = result.get("formatted_address", location)
        return loc["lat"], loc["lng"], formatted

    # ------------------------------------------------------------------
    # Search Indian vegetarian restaurants via Places Text Search
    # ------------------------------------------------------------------
    def search_indian_vegetarian(
        self, lat: float, lng: float, radius_m: int = 8000
    ) -> list[Restaurant]:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.maps_api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        }
        body = {
            "textQuery": "Indian vegetarian restaurant",
            "includedType": "restaurant",
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": radius_m,
                }
            },
            "pageSize": 20,
        }

        all_places: list[dict] = []
        page_token = None

        for page in range(1, MAX_PAGES + 1):
            if page_token:
                body["pageToken"] = page_token
                time.sleep(PAGE_FETCH_DELAY)

            log.info("Fetching results page %d...", page)
            resp = self.session.post(
                TEXT_SEARCH_URL, headers=headers, json=body, timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()

            places = data.get("places", [])
            all_places.extend(places)

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        restaurants = [Restaurant.from_api(p) for p in all_places]

        # Keep it strictly relevant: filter out anything that isn't
        # actually an Indian / vegetarian-flagged place if the API
        # returned noise (text search is fuzzy).
        def is_relevant(r: Restaurant) -> bool:
            name_lower = r.name.lower()
            type_str = " ".join(r.types).lower()
            return (
                r.serves_vegetarian is True
                or "indian" in name_lower
                or "vegetarian" in name_lower
                or "vegan" in name_lower
                or "indian_restaurant" in type_str
                or "vegetarian_restaurant" in type_str
            )

        filtered = [r for r in restaurants if is_relevant(r)]
        # De-duplicate by name+address, sort by rating desc
        seen = set()
        deduped = []
        for r in sorted(filtered, key=lambda x: (x.rating or 0), reverse=True):
            key = (r.name, r.address)
            if key not in seen:
                seen.add(key)
                deduped.append(r)

        return deduped

    # ------------------------------------------------------------------
    # Ask Gemini for a short human-readable summary/recommendation
    # ------------------------------------------------------------------
    def summarize_with_gemini(self, restaurants: list[Restaurant], location: str) -> str:
        if not restaurants:
            return "No matching restaurants to summarize."

        payload = [r.to_dict() for r in restaurants]
        prompt = f"""
You are a food recommendation assistant. Below is a verified list of Indian
vegetarian restaurants near "{location}", returned from Google Places
(all already confirmed Indian and/or vegetarian - do not second-guess this).

{json.dumps(payload, indent=2)}

Please provide, using only the data given:
1. Top 5 picks overall (ranked)
2. Highest rated option
3. Best option for a family outing
4. Most budget-friendly option (based on priceLevel if available)
5. A one-line recommendation for each restaurant in the list

Keep it concise and skip any restaurant fields that are missing/unknown
rather than guessing.
"""
        response = self.client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        return response.text


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def load_api_keys() -> tuple[str, str]:
    gemini_key = os.getenv("GEMINI_API_KEY")
    maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    missing = [
        name
        for name, val in [("GEMINI_API_KEY", gemini_key), ("GOOGLE_MAPS_API_KEY", maps_key)]
        if not val
    ]
    if missing:
        raise RestaurantFinderError(f"Missing required environment variable(s): {', '.join(missing)}")
    return gemini_key, maps_key


def print_restaurants(restaurants: list[Restaurant]) -> None:
    if not restaurants:
        print("\nNo Indian vegetarian restaurants found in this area.\n")
        return

    print(f"\nFound {len(restaurants)} Indian vegetarian restaurant(s):\n")
    for i, r in enumerate(restaurants, 1):
        rating_str = f"{r.rating}★ ({r.rating_count} reviews)" if r.rating else "No rating yet"
        veg_str = "Confirmed vegetarian" if r.serves_vegetarian else "Vegetarian (name-based match)"
        open_str = (
            "Open now" if r.open_now is True else "Closed now" if r.open_now is False else "Hours unknown"
        )
        print(f"{i}. {r.name}")
        print(f"   Address : {r.address}")
        print(f"   Rating  : {rating_str}")
        print(f"   Status  : {open_str} | {veg_str}")
        if r.website:
            print(f"   Website : {r.website}")
        if r.maps_url:
            print(f"   Maps    : {r.maps_url}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find Indian vegetarian restaurants near a ZIP code or location."
    )
    parser.add_argument(
        "location",
        nargs="?",
        help="ZIP code, city, or address (e.g. '75087' or 'Rockwall, TX'). "
        "If omitted, you'll be prompted.",
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=8000,
        help="Search radius in meters (default: 8000 = 8km)",
    )
    parser.add_argument(
        "--no-ai-summary",
        action="store_true",
        help="Skip the Gemini-generated summary and just print raw results.",
    )
    args = parser.parse_args()

    location = args.location or input("Enter ZIP code or location: ").strip()
    if not location:
        print("A ZIP code or location is required.")
        sys.exit(1)

    try:
        gemini_key, maps_key = load_api_keys()
        finder = IndianVegRestaurantFinder(gemini_key, maps_key)

        lat, lng, resolved_address = finder.geocode(location)
        print(f"\nResolved location: {resolved_address}  ({lat:.5f}, {lng:.5f})")

        restaurants = finder.search_indian_vegetarian(lat, lng, radius_m=args.radius)
        print_restaurants(restaurants)

        if not args.no_ai_summary and restaurants:
            print("=" * 60)
            print("AI Recommendation Summary")
            print("=" * 60)
            print(finder.summarize_with_gemini(restaurants, resolved_address))

    except RestaurantFinderError as e:
        log.error(str(e))
        sys.exit(1)
    except requests.HTTPError as e:
        log.error("API request failed: %s", e)
        sys.exit(1)
    except requests.RequestException as e:
        log.error("Network error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
