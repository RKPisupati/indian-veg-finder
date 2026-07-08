# Thali Finder — Indian Vegetarian Restaurant Finder

A small local web app: enter a ZIP code or city, get a list of Indian
vegetarian restaurants nearby (pulled from Google Places), plus an optional
AI-written recommendation summary.
# Simple Architecture 

                         🍽️ AI Restaurant Recommendation Assistant

┌──────────────────────┐
│ 👤 User              │
│----------------------│
│ • ZIP Code           │
│ • Cuisine            │
│ • Budget             │
│ • Family / Veg       │
└──────────┬───────────┘
           │
           ▼
┌─────────────────────────────────────────────┐
│ 🐍 Python Application (FastAPI / Flask)     │
│---------------------------------------------│
│ ✔ Receives User Request                     │
│ ✔ Calls External APIs                       │
│ ✔ Builds Gemini Prompt                      │
│ ✔ Returns AI Response                       │
└───────┬───────────────┬─────────────────────┘
        │               │
        │               │
        ▼               ▼
┌────────────────┐   ┌────────────────────────┐
│ 📍 Geocoding   │   │ 🍴 Google Places API    │
│ API            │   │------------------------│
│                │   │ Nearby Restaurants     │
│ ZIP → Lat/Lng  │   │ Ratings                │
│                │   │ Address                │
└───────┬────────┘   │ Website                │
        │            │ Maps Link              │
        └──────┬─────┴────────────────────────┘
               │
               ▼
      Restaurant Information (JSON)
               │
               ▼
┌─────────────────────────────────────────────┐
│ 🤖 Google Gemini                            │
│---------------------------------------------│
│ • Analyze Restaurant Data                   │
│ • Recommend Best Restaurant                 │
│ • Suggest Family Friendly                   │
│ • Suggest Vegetarian Options                │
│ • Explain Why                               │
└───────────────┬─────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────┐
│ 📱 Final Response                           │
│---------------------------------------------│
│ ⭐ Top 5 Restaurants                        │
│ 🍛 Best Cuisine                             │
│ 👨‍👩‍👧 Family Recommendation                 │
│ 🌱 Vegetarian Options                       │
│ 📍 Google Maps Link                         │
└─────────────────────────────────────────────┘
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/2f167d32-7b82-4c47-8d2a-b4e97d64b247" />
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/f79d9e20-882c-4d9a-bbe8-edf8cc206453" />


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
   <img width="1273" height="347" alt="image" src="https://github.com/user-attachments/assets/8b7834f5-8c60-4cde-b4aa-04d14f6be342" />


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
