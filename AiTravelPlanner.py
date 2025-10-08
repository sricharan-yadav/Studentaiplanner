import os
import requests
import folium
from geopy.geocoders import Nominatim
import pandas as pd
from datetime import datetime, timedelta, date
import random
import math
import json
from typing import List, Dict, Any, Tuple
import streamlit as st
from streamlit_folium import st_folium
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# -------------------------------------
# API Configuration (Replace if needed)
# -------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "your_google_maps_api_key_here")

geolocator = Nominatim(user_agent="student_travel_planner")

# ------------------------------
# CLASS: StudentTravelPlanner
# ------------------------------
class StudentTravelPlanner:
    def __init__(self):
        self.transportation_options = {
            'walking': {'cost_per_km': 0, 'speed_kmh': 5},
            'public_transport': {'cost_per_km': 12.5, 'speed_kmh': 20},
            'bike_rental': {'cost_per_km': 8.5, 'speed_kmh': 12},
            'ride_share': {'cost_per_km': 100.0, 'speed_kmh': 25}
        }

        self.accommodation_options = {
            'hostel': {'cost_per_night': 1600, 'comfort': 'basic'},
            'budget_hotel': {'cost_per_night': 3700, 'comfort': 'standard'},
            'airbnb_shared': {'cost_per_night': 2500, 'comfort': 'standard'},
            'airbnb_private': {'cost_per_night': 5000, 'comfort': 'good'}
        }

        self.food_options = {
            'street_food': {'cost_per_meal': 400, 'experience': 'local'},
            'budget_restaurant': {'cost_per_meal': 800, 'experience': 'standard'},
            'cooking': {'cost_per_meal': 250, 'experience': 'homely'},
            'mid_range_restaurant': {'cost_per_meal': 1200, 'experience': 'nice'}
        }

    # -------------------
    # Helper Methods
    # -------------------
    def geocode_location(self, location: str) -> Tuple[float, float] | None:
        try:
            loc = geolocator.geocode(location, timeout=10)
            if loc:
                return loc.latitude, loc.longitude
        except Exception:
            pass
        return None

    def get_nearby_places(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        sample_places = [
            {"name": "Central Park", "lat": lat + 0.01, "lon": lon + 0.01},
            {"name": "History Museum", "lat": lat - 0.01, "lon": lon + 0.01},
            {"name": "Art Gallery", "lat": lat + 0.01, "lon": lon - 0.01},
            {"name": "River Walk", "lat": lat - 0.01, "lon": lon - 0.01},
            {"name": "City Zoo", "lat": lat + 0.02, "lon": lon + 0.02},
            {"name": "Botanical Garden", "lat": lat - 0.02, "lon": lon - 0.02},
        ]
        return random.sample(sample_places, min(len(sample_places), 4))

    def allocate_budget(self, budget: int, days: int) -> Dict[str, float]:
        daily = budget / max(days, 1)
        return {
            "accommodation": round(daily * 0.4, 2),
            "food": round(daily * 0.25, 2),
            "transport": round(daily * 0.2, 2),
            "activities": round(daily * 0.15, 2)
        }

    def select_accommodation(self, preferred_stay: str) -> Dict[str, Any]:
        """Select accommodation based on preferred stay type."""
        if preferred_stay in self.accommodation_options:
            return {"name": preferred_stay, **self.accommodation_options[preferred_stay]}
        else:
            return {"name": "hostel", **self.accommodation_options["hostel"]}

    def select_transportation(self, preferred_transport: str) -> Dict[str, Any]:
        """Select transportation based on user's choice."""
        if preferred_transport in self.transportation_options:
            return {"mode": preferred_transport, "cost": random.randint(40, 120), "time_minutes": random.randint(15, 45)}
        else:
            return {"mode": "public_transport", "cost": 50, "time_minutes": 30}

    def generate_ai_description(self, location: str, interests: str, days: int, style: str, transport: str, stay: str) -> str:
        return f"A {days}-day {style} trip in {location}, exploring {interests}. Preferred transport: {transport}, Stay: {stay}."

    def create_itinerary_map(self, itinerary: Dict[str, Any]) -> folium.Map:
        lat, lon = itinerary["coordinates"]
        fmap = folium.Map(location=[lat, lon], zoom_start=13)
        for d in itinerary["itinerary"]:
            for act in d["activities"]:
                folium.Marker(
                    [act.get("lat", lat), act.get("lon", lon)],
                    popup=act["name"]
                ).add_to(fmap)
        return fmap

    def calculate_total_cost(self, itinerary: Dict[str, Any]) -> float:
        total = 0
        for d in itinerary["itinerary"]:
            total += d["accommodation"]["cost_per_night"]
            for m in d["meals"]:
                total += m["cost"]
            for act in d["activities"]:
                total += act["estimated_cost"] + act["transport"]["cost"]
        return round(total, 2)

    def create_pdf_bytes(self, itinerary: Dict[str, Any]) -> bytes:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica", 12)
        c.drawString(100, 800, f"Trip Itinerary - {itinerary['location']}")
        c.drawString(100, 780, f"Duration: {itinerary['days']} days")
        c.drawString(100, 760, f"Budget: ₹{itinerary['budget']}")
        c.drawString(100, 740, f"Preferred Transport: {itinerary['preferred_transport']}")
        c.drawString(100, 720, f"Preferred Stay: {itinerary['preferred_stay']}")

        y = 700
        for i, d in enumerate(itinerary["itinerary"], 1):
            c.drawString(100, y, f"Day {i}: {d['date']}")
            y -= 20
            c.drawString(120, y, f"Stay: {d['accommodation']['name'].title()}")
            y -= 20
            for act in d["activities"]:
                c.drawString(140, y, f"- {act['time_slot']}: {act['name']}")
                y -= 20
            if y < 100:
                c.showPage()
                y = 800
        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    def generate_itinerary(self, location: str, interests: str, budget: int, days: int,
                           travel_style: str, start_date: date, preferred_transport: str, preferred_stay: str) -> Dict[str, Any]:
        coords = self.geocode_location(location)
        if not coords:
            return {"error": f"Could not find coordinates for {location}"}
        lat, lon = coords

        daily_budget = self.allocate_budget(budget, days)
        all_places = self.get_nearby_places(lat, lon)

        itinerary_days = []
        current_date = start_date
        for d in range(days):
            accommodation = self.select_accommodation(preferred_stay)
            meals = [
                {"meal": "breakfast", "type": "street_food", "cost": self.food_options["street_food"]["cost_per_meal"]},
                {"meal": "lunch", "type": "budget_restaurant", "cost": self.food_options["budget_restaurant"]["cost_per_meal"]},
                {"meal": "dinner", "type": "mid_range_restaurant", "cost": self.food_options["mid_range_restaurant"]["cost_per_meal"]},
            ]

            day_places = random.sample(all_places, min(2, len(all_places)))
            activities = []
            for i, place in enumerate(day_places):
                activities.append({
                    "time_slot": "Morning" if i == 0 else "Afternoon",
                    "name": place["name"],
                    "lat": place["lat"],
                    "lon": place["lon"],
                    "estimated_cost": random.randint(200, 800),
                    "transport": self.select_transportation(preferred_transport)
                })

            itinerary_days.append({
                "date": str(current_date),
                "accommodation": accommodation,
                "meals": meals,
                "activities": activities
            })
            current_date += timedelta(days=1)

        ai_desc = self.generate_ai_description(location, interests, days, travel_style, preferred_transport, preferred_stay)

        return {
            "location": location,
            "budget": budget,
            "days": days,
            "ai_description": ai_desc,
            "daily_budget_allocation": daily_budget,
            "itinerary": itinerary_days,
            "coordinates": (lat, lon),
            "preferred_transport": preferred_transport,
            "preferred_stay": preferred_stay
        }

# ------------------------------
# STREAMLIT APP
# ------------------------------
def main():
    st.set_page_config(page_title="AI Travel Planner for Students (INR)", layout="wide")
    st.title("🎒 AI Travel Planner for Students (INR)")

    planner = StudentTravelPlanner()

    with st.sidebar:
        st.header("Trip Details")
        location = st.text_input("Destination City", "Paris, France")
        interests = st.text_input("Interests (comma separated)", "culture, food, nature")
        budget = st.number_input("Total Budget (INR)", min_value=1000, max_value=500000, value=40000, step=500)
        days = st.slider("Trip Duration (days)", 1, 14, 5)
        start_date = st.date_input("Start Date", datetime.now().date())
        travel_style = st.selectbox("Travel Style", ["budget", "comfort", "adventure"])

        preferred_transport = st.selectbox(
            "Preferred Transport",
            ["walking", "public_transport", "bike_rental", "ride_share"]
        )
        preferred_stay = st.selectbox(
            "Preferred Stay Destination",
            ["hostel", "budget_hotel", "airbnb_shared", "airbnb_private"]
        )

        if st.button("Generate Itinerary", type="primary"):
            with st.spinner("Creating your personalized itinerary..."):
                itinerary = planner.generate_itinerary(
                    location, interests, budget, days, travel_style, start_date, preferred_transport, preferred_stay
                )
                if "error" in itinerary:
                    st.error(f"Error: {itinerary['error']}")
                else:
                    st.session_state.itinerary = itinerary

    if "itinerary" in st.session_state:
        itinerary = st.session_state.itinerary

        st.subheader("🌟 Your Personalized Itinerary")
        st.info(itinerary['ai_description'])

        st.subheader("💰 Daily Budget Breakdown")
        st.json(itinerary['daily_budget_allocation'])

        st.subheader("📅 Daily Plans")
        for i, day in enumerate(itinerary['itinerary']):
            with st.expander(f"Day {i+1} - {day['date']}"):
                st.write(f"**Accommodation**: {day['accommodation']['name']} (₹{day['accommodation']['cost_per_night']}/night)")
                st.write("**Meals**:")
                for m in day['meals']:
                    st.write(f"- {m['meal'].title()}: {m['type']} (₹{m['cost']})")
                st.write("**Activities**:")
                for act in day['activities']:
                    st.write(f"- {act['time_slot']}: {act['name']} (₹{act['estimated_cost']}, Transport ₹{act['transport']['cost']})")

        st.subheader("🗺️ Itinerary Map")
        fmap = planner.create_itinerary_map(itinerary)
        st_folium(fmap, width=700, height=500)

        total_cost = planner.calculate_total_cost(itinerary)
        st.subheader("💵 Cost Summary")
        st.write(f"**Estimated Total Cost**: ₹{total_cost:.2f}")
        st.write(f"**Remaining Budget**: ₹{itinerary['budget'] - total_cost:.2f}")

        st.download_button(
            label="Download Itinerary as JSON",
            data=json.dumps(itinerary, indent=2),
            file_name=f"itinerary_{location.replace(' ', '_')}.json",
            mime="application/json"
        )

        pdf_bytes = planner.create_pdf_bytes(itinerary)
        st.download_button(
            label="Download Itinerary as PDF",
            data=pdf_bytes,
            file_name=f"itinerary_{location.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )

if __name__ == "__main__":
    main()
