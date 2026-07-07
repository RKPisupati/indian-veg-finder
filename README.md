# Thali Finder — Indian Vegetarian Restaurant Finder

A small local web app: enter a ZIP code or city, get a list of Indian
vegetarian restaurants nearby (pulled from Google Places), plus an optional
AI-written recommendation summary.

## Files

- `indian_veg_finder.py` — all the search/geocoding logic (also runnable on its own as a CLI)
- `app.py` — Flask server that wraps that logic and serves the UI
- `templates/index.html` — the browser UI (self-contained: HTML + CSS + JS)

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set your API keys (same two keys as before):
   ```bash
   export GEMINI_API_KEY="your-gemini-key"
   export GOOGLE_MAPS_API_KEY="your-maps-key"
   ```
   On Windows (PowerShell): `$env:GEMINI_API_KEY="..."`

3. Run the server:
   ```bash
   python app.py
   ```

   This starts a local server at `http://127.0.0.1:5050` and automatically
   opens it in your default browser. If it doesn't open automatically, just
   visit that URL yourself.

4. Type a ZIP code or city into the search bar, pick a radius, and hit
   **Search**. Results appear as cards; a green square-with-dot mark (the
   familiar Indian "vegetarian" symbol) means Google has confirmed the
   place serves vegetarian food — an amber version means it's a likely
   match based on the name only.

## Notes

- Everything runs locally — no data leaves your machine except the calls to
  Google Places/Geocoding and the Gemini API.
- The CLI version still works unchanged: `python indian_veg_finder.py 75087`
- To stop the server, press `Ctrl+C` in the terminal.
