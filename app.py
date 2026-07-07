#!/usr/bin/env python3
"""
Flask backend for the Indian Vegetarian Restaurant Finder UI.
Wraps indian_veg_finder.py — no logic is duplicated here.

Run:
    python app.py
Then open:
    http://127.0.0.1:5050
"""

import os
import threading
import webbrowser

from flask import Flask, jsonify, render_template, request

from indian_veg_finder import IndianVegRestaurantFinder, RestaurantFinderError

app = Flask(__name__)

PORT = 5050


def get_finder() -> IndianVegRestaurantFinder:
    gemini_key = os.getenv("GEMINI_API_KEY")
    maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
    missing = [
        name
        for name, val in [("GEMINI_API_KEY", gemini_key), ("GOOGLE_MAPS_API_KEY", maps_key)]
        if not val
    ]
    if missing:
        raise RestaurantFinderError(
            f"Missing environment variable(s): {', '.join(missing)}. "
            "Set them, then restart the server."
        )
    return IndianVegRestaurantFinder(gemini_key, maps_key)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search")
def api_search():
    location = request.args.get("location", "").strip()
    radius = request.args.get("radius", "8000")
    include_summary = request.args.get("summary", "true").lower() == "true"

    if not location:
        return jsonify({"error": "Enter a ZIP code or location to search."}), 400

    try:
        radius_m = max(500, min(int(radius), 50000))
    except ValueError:
        radius_m = 8000

    try:
        finder = get_finder()
        lat, lng, resolved = finder.geocode(location)
        restaurants = finder.search_indian_vegetarian(lat, lng, radius_m=radius_m)

        summary = None
        if include_summary and restaurants:
            summary = finder.summarize_with_gemini(restaurants, resolved)

        return jsonify(
            {
                "resolved_location": resolved,
                "lat": lat,
                "lng": lng,
                "radius_m": radius_m,
                "count": len(restaurants),
                "restaurants": [r.to_dict() for r in restaurants],
                "summary": summary,
            }
        )
    except RestaurantFinderError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:  # noqa: BLE001 - surface to UI as a friendly error
        return jsonify({"error": f"Search failed: {e}"}), 500


if __name__ == "__main__":
    url = f"http://127.0.0.1:{PORT}"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"\nIndian Vegetarian Restaurant Finder running at {url}\n")
    app.run(host="127.0.0.1", port=PORT, debug=False)
