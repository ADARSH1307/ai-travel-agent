import streamlit as st
import json
import os
import requests
from agno.agent import Agent
from agno.tools.serpapi import SerpApiTools
from agno.models.google import Gemini
from datetime import datetime, timedelta
import re

# Initialize session state
if 'itinerary_generated' not in st.session_state:
    st.session_state.itinerary_generated = False
if 'itinerary_content' not in st.session_state:
    st.session_state.itinerary_content = ""
if 'hotel_restaurant_content' not in st.session_state:
    st.session_state.hotel_restaurant_content = ""
if 'cheapest_flights' not in st.session_state:
    st.session_state.cheapest_flights = []
if 'critic_feedback' not in st.session_state:
    st.session_state.critic_feedback = ""
if 'travel_theme' not in st.session_state:
    st.session_state.travel_theme = ""
if 'destination' not in st.session_state:
    st.session_state.destination = ""
if 'departure_date' not in st.session_state:
    st.session_state.departure_date = ""
if 'return_date' not in st.session_state:
    st.session_state.return_date = ""

# Streamlit UI Setup
st.set_page_config(page_title="🌍 AI Travel Planner", layout="wide")
st.markdown(
    """
    <style>
        .title {
            text-align: center;
            font-size: 36px;
            font-weight: bold;
            color: #ff5733;
        }
        .subtitle {
            text-align: center;
            font-size: 20px;
            color: #555;
        }
        .stSlider > div {
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Title and subtitle
st.markdown('<h1 class="title">✈️ AI-Powered Travel Planner</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Plan your dream trip with AI! Get personalized recommendations for flights, hotels, and activities.</p>', unsafe_allow_html=True)

# Inputs
st.markdown("### 🌍 Where are you headed?")
source = st.text_input("🛫 Departure City (IATA Code):", "BOM")
destination = st.text_input("🛬 Destination (IATA Code):", "DEL")

st.markdown("### 📅 Plan Your Adventure")
num_days = st.slider("🕒 Trip Duration (days):", 1, 14, 5)
travel_theme = st.selectbox(
    "🎭 Select Your Travel Theme:",
    ["💑 Couple Getaway", "👨‍👩‍👧‍👦 Family Vacation", "🏔️ Adventure Trip", "🧳 Solo Exploration"]
)

st.markdown("---")

st.markdown(
    f"""
    <div style="
        text-align: center; 
        padding: 15px; 
        background-color: #ffecd1; 
        border-radius: 10px; 
        margin-top: 20px;
    ">
        <h3>🌟 Your {travel_theme} to {destination} is about to begin! 🌟</h3>
        <p>Let's find the best flights, stays, and experiences for your unforgettable journey.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

def format_datetime(iso_string):
    try:
        dt = datetime.strptime(iso_string, "%Y-%m-%d %H:%M")
        return dt.strftime("%b-%d, %Y | %I:%M %p")
    except:
        return "N/A"

activity_preferences = st.text_area(
    "🌍 What activities do you enjoy? (e.g., relaxing on the beach, exploring historical sites, nightlife, adventure)",
    "Relaxing on the beach, exploring historical sites"
)

departure_date = st.date_input("Departure Date")
return_date = st.date_input("Return Date")

# Sidebar
st.sidebar.title("🌎 Travel Assistant")
st.sidebar.subheader("Personalize Your Trip")
budget = st.sidebar.radio("💰 Budget Preference:", ["Economy", "Standard", "Luxury"])
flight_class = st.sidebar.radio("✈️ Flight Class:", ["Economy", "Business", "First Class"])
hotel_rating = st.sidebar.selectbox("🏨 Preferred Hotel Rating:", ["Any", "3⭐", "4⭐", "5⭐"])

st.sidebar.subheader("🎒 Packing Checklist")
packing_list = {
    "👕 Clothes": True,
    "🩴 Comfortable Footwear": True,
    "🕶️ Sunglasses & Sunscreen": False,
    "📖 Travel Guidebook": False,
    "💊 Medications & First-Aid": True
}
for item, checked in packing_list.items():
    st.sidebar.checkbox(item, value=checked)

st.sidebar.subheader("🛂 Travel Essentials")
visa_required = st.sidebar.checkbox("🛃 Check Visa Requirements")
travel_insurance = st.sidebar.checkbox("🛡️ Get Travel Insurance")
currency_converter = st.sidebar.checkbox("💱 Currency Exchange Rates")

# API Keys
SERPAPI_KEY = "46ccc6191f89be8fe2f0c140387d7880a32fb0938a4a0a9d5c58033088a96ee1"
GOOGLE_API_KEY = "AIzaSyAgP1MWM_iVLE5hVQJt3MJHFgUg-P_lYaM"
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# Replacement for GoogleSearch
def serpapi_flight_search(params):
    url = "https://serpapi.com/search"
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error from SerpAPI: {response.status_code} - {response.text}")
        return {}

# Fetch flights
def fetch_flights(source, destination, departure_date, return_date):
    params = {
        "engine": "google_flights",
        "departure_id": source,
        "arrival_id": destination,
        "outbound_date": str(departure_date),
        "return_date": str(return_date),
        "currency": "INR",
        "hl": "en",
        "api_key": SERPAPI_KEY
    }
    return serpapi_flight_search(params)

# Extract flights
def extract_cheapest_flights(flight_data):
    best_flights = flight_data.get("best_flights", [])
    sorted_flights = sorted(best_flights, key=lambda x: x.get("price", float("inf")))[:3]
    return sorted_flights

# AI Agents
@st.cache_resource
def get_agents():
    researcher = Agent(
        name="Researcher",
        instructions=[
            "Identify the travel destination specified by the user.",
            "Gather detailed information on the destination, including climate, culture, and safety tips.",
            "Find popular attractions, landmarks, and must-visit places.",
            "Search for activities that match the user's interests and travel style.",
            "Prioritize information from reliable sources and official travel guides.",
            "Provide well-structured summaries with key insights and recommendations."
        ],
        model=Gemini(id="gemini-2.0-flash-exp"),
        tools=[SerpApiTools(api_key=SERPAPI_KEY)],
        add_datetime_to_instructions=True,
    )

    planner = Agent(
        name="Planner",
        instructions=[
            "Gather details about the user's travel preferences and budget.",
            "Create a detailed itinerary with scheduled activities and estimated costs.",
            "Structure the itinerary with clear day-by-day format like 'Day 1:', 'Day 2:', etc.",
            "Include specific times for activities (e.g., '9:00 AM - Visit Red Fort', '2:00 PM - Lunch at Restaurant').",
            "Ensure the itinerary includes transportation options and travel time estimates.",
            "Optimize the schedule for convenience and enjoyment.",
            "Present the itinerary in a structured format with bullet points or numbered lists for each day."
        ],
        model=Gemini(id="gemini-2.0-flash-exp"),
        add_datetime_to_instructions=True,
    )

    hotel_restaurant_finder = Agent(
        name="Hotel & Restaurant Finder",
        instructions=[
            "Identify key locations in the user's travel itinerary.",
            "Search for highly rated hotels near those locations.",
            "Search for top-rated restaurants based on cuisine preferences and proximity.",
            "Prioritize results based on user preferences, ratings, and availability.",
            "Provide direct booking links or reservation options where possible."
        ],
        model=Gemini(id="gemini-2.0-flash-exp"),
        tools=[SerpApiTools(api_key=SERPAPI_KEY)],
        add_datetime_to_instructions=True,
    )

    critic = Agent(
        name="CriticAgent",
        instructions=[
            "Review the itinerary for pacing, feasibility, and travel fatigue.",
            "Suggest adjustments to improve user comfort and optimize routes.",
            "Flag days that may be overloaded with activities."
        ],
        model=Gemini(id="gemini-2.0-flash-exp")
    )
    
    return researcher, planner, hotel_restaurant_finder, critic

researcher, planner, hotel_restaurant_finder, critic = get_agents()

# Google Services Setup
def setup_google_services():
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import pickle
        
        SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/gmail.send"]
        
        creds = None
        if os.path.exists("token.pkl"):
            with open("token.pkl", "rb") as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists("credentials.json"):
                    st.error("❌ Google credentials.json file not found. Please add your Google API credentials file.")
                    return None, None
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open("token.pkl", "wb") as token:
                pickle.dump(creds, token)
        
        calendar_service = build("calendar", "v3", credentials=creds)
        gmail_service = build("gmail", "v1", credentials=creds)
        return calendar_service, gmail_service
    
    except ImportError:
        st.error("❌ Google API libraries not installed. Please install: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return None, None
    except Exception as e:
        st.error(f"❌ Error setting up Google services: {str(e)}")
        return None, None

# Enhanced Calendar Integration Functions
def add_events_to_calendar(calendar_service, itinerary_text, departure_date):
    """
    Enhanced function to add travel itinerary events to Google Calendar
    """
    try:
        events_added = 0
        lines = itinerary_text.split("\n")
        current_day = 0
        current_date = departure_date
        
        # Enhanced patterns to detect days and activities
        day_patterns = [
            r'day\s*(\d+)',
            r'(\d+)\s*day',
            r'day\s*(\d+)\s*:',
            r'(\d+)\s*\.',
            r'(\d+)\s*-'
        ]
        
        # Time patterns to detect activities with times
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)',
            r'(\d{1,2}):(\d{2})',
            r'(\d{1,2})\s*(AM|PM|am|pm)',
            r'morning|afternoon|evening|night'
        ]
        
        # Activity indicators
        activity_indicators = [
            'visit', 'explore', 'tour', 'see', 'go to', 'check out', 'experience',
            'breakfast', 'lunch', 'dinner', 'meal', 'restaurant', 'cafe',
            'museum', 'temple', 'church', 'palace', 'fort', 'beach', 'park',
            'shopping', 'market', 'show', 'performance', 'activity'
        ]
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            # Check if this is a day header
            day_found = False
            for pattern in day_patterns:
                match = re.search(pattern, line.lower())
                if match:
                    try:
                        day_num = int(match.group(1))
                        current_day = day_num - 1
                        current_date = departure_date + timedelta(days=current_day)
                        day_found = True
                        break
                    except (IndexError, ValueError):
                        continue
            
            if day_found:
                continue
            
            # Check if this line contains an activity
            line_lower = line.lower()
            is_activity = any(indicator in line_lower for indicator in activity_indicators)
            
            # If it's an activity or contains time information
            if is_activity or any(re.search(pattern, line) for pattern in time_patterns):
                
                # Try to extract time information
                time_found = False
                start_hour = 9  # Default start time
                start_minute = 0
                
                for pattern in time_patterns:
                    time_match = re.search(pattern, line)
                    if time_match:
                        try:
                            if len(time_match.groups()) >= 2:
                                hour = int(time_match.group(1))
                                minute = int(time_match.group(2))
                                am_pm = time_match.group(3) if len(time_match.groups()) >= 3 else None
                                
                                if am_pm and am_pm.upper() == 'PM' and hour != 12:
                                    hour += 12
                                elif am_pm and am_pm.upper() == 'AM' and hour == 12:
                                    hour = 0
                                
                                start_hour = hour
                                start_minute = minute
                                time_found = True
                                break
                            elif 'morning' in line_lower:
                                start_hour = 9
                            elif 'afternoon' in line_lower:
                                start_hour = 14
                            elif 'evening' in line_lower:
                                start_hour = 18
                            elif 'night' in line_lower:
                                start_hour = 20
                        except (ValueError, IndexError):
                            continue
                
                # If no specific time found, assign based on order of activities in the day
                if not time_found:
                    # Count activities already processed for this day
                    activities_today = 0
                    for prev_line in lines[:line_num]:
                        if any(indicator in prev_line.lower() for indicator in activity_indicators):
                            activities_today += 1
                    
                    # Assign times throughout the day
                    start_times = [9, 11, 14, 16, 18, 20]  # 9 AM, 11 AM, 2 PM, 4 PM, 6 PM, 8 PM
                    if activities_today < len(start_times):
                        start_hour = start_times[activities_today]
                    else:
                        start_hour = 9 + (activities_today * 2) % 12
                
                # Clean up the activity title
                activity_title = line.strip()
                # Remove common prefixes
                prefixes_to_remove = ['-', '•', '*', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.']
                for prefix in prefixes_to_remove:
                    if activity_title.startswith(prefix):
                        activity_title = activity_title[len(prefix):].strip()
                
                # Limit title length
                if len(activity_title) > 100:
                    activity_title = activity_title[:97] + "..."
                
                # Create the calendar event
                try:
                    start_datetime = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=start_hour, minutes=start_minute)
                    end_datetime = start_datetime + timedelta(hours=2)  # 2-hour duration
                    
                    event = {
                        "summary": activity_title,
                        "start": {
                            "dateTime": start_datetime.isoformat(),
                            "timeZone": "Asia/Kolkata"
                        },
                        "end": {
                            "dateTime": end_datetime.isoformat(),
                            "timeZone": "Asia/Kolkata"
                        },
                        "description": f"Travel itinerary activity\nOriginal: {line}"
                    }
                    
                    # Add the event to calendar
                    result = calendar_service.events().insert(calendarId="primary", body=event).execute()
                    events_added += 1
                    
                except Exception as e:
                    continue
        
        return events_added
        
    except Exception as e:
        return 0

def create_basic_day_events(calendar_service, itinerary_text, departure_date):
    """
    Create basic daily events as a fallback
    """
    try:
        events_added = 0
        
        # Find day mentions in the itinerary
        day_pattern = r'day\s*(\d+)'
        days_found = set()
        
        for match in re.finditer(day_pattern, itinerary_text.lower()):
            try:
                day_num = int(match.group(1))
                days_found.add(day_num)
            except ValueError:
                continue
        
        # If no days found, create events for the number of trip days
        if not days_found:
            # Estimate from departure and return dates
            trip_duration = (st.session_state.return_date - st.session_state.departure_date).days + 1
            days_found = set(range(1, trip_duration + 1))
        
        for day_num in sorted(days_found):
            try:
                event_date = departure_date + timedelta(days=day_num - 1)
                start_datetime = datetime.combine(event_date, datetime.min.time()) + timedelta(hours=9)
                end_datetime = start_datetime + timedelta(hours=8)
                
                event = {
                    "summary": f"Travel Day {day_num} - {st.session_state.destination}",
                    "start": {
                        "dateTime": start_datetime.isoformat(),
                        "timeZone": "Asia/Kolkata"
                    },
                    "end": {
                        "dateTime": end_datetime.isoformat(),
                        "timeZone": "Asia/Kolkata"
                    },
                    "description": f"Travel itinerary for Day {day_num}\n\nFull itinerary:\n{itinerary_text[:500]}..."
                }
                
                calendar_service.events().insert(calendarId="primary", body=event).execute()
                events_added += 1
                
            except Exception as e:
                continue
        
        return events_added
        
    except Exception as e:
        return 0

def handle_calendar_integration():
    """
    Handle the calendar integration with multiple fallback strategies
    """
    calendar_service, _ = setup_google_services()
    if not calendar_service:
        st.error("❌ Could not connect to Google Calendar. Please check your credentials.")
        return
    
    with st.spinner("📅 Adding events to Google Calendar..."):
        # Strategy 1: Try enhanced parsing
        events_added = add_events_to_calendar(calendar_service, st.session_state.itinerary_content, st.session_state.departure_date)
        
        # Strategy 2: Create basic day-by-day events as fallback
        if events_added == 0:
            events_added = create_basic_day_events(calendar_service, st.session_state.itinerary_content, st.session_state.departure_date)
        
        if events_added > 0:
            st.success(f"✅ {events_added} events added to Google Calendar!")
        else:
            st.error("❌ Could not add any events to calendar. Please check your itinerary format or Google Calendar permissions.")

def send_email_itinerary(gmail_service, subject, body_html, to_email):
    try:
        import base64
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = "me"
        msg["To"] = to_email
        msg.attach(MIMEText(body_html, "html"))
        
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error sending email: {str(e)}")
        return False

# Generate Plan Button
if st.button("🚀 Generate Travel Plan", key="generate_plan_button"):
    try:
        with st.spinner("✈️ Fetching best flight options..."):
            flight_data = fetch_flights(source, destination, departure_date, return_date)
            cheapest_flights = extract_cheapest_flights(flight_data)
            st.session_state.cheapest_flights = cheapest_flights

        with st.spinner("🔍 Researching best attractions & activities..."):
            research_prompt = (
                f"Research the best attractions and activities in {destination} for a {num_days}-day {travel_theme.lower()} trip. "
                f"The traveler enjoys: {activity_preferences}. Budget: {budget}. Flight Class: {flight_class}. "
                f"Hotel Rating: {hotel_rating}. Visa Requirement: {visa_required}. Travel Insurance: {travel_insurance}."
            )
            research_results = researcher.run(research_prompt, stream=False)

        with st.spinner("🏨 Searching for hotels & restaurants..."):
            hotel_restaurant_prompt = (
                f"Find the best hotels and restaurants near popular attractions in {destination} for a {travel_theme.lower()} trip. "
                f"Budget: {budget}. Hotel Rating: {hotel_rating}. Preferred activities: {activity_preferences}."
            )
            hotel_restaurant_results = hotel_restaurant_finder.run(hotel_restaurant_prompt, stream=False)
            st.session_state.hotel_restaurant_content = hotel_restaurant_results.content

        with st.spinner("🗺️ Creating your personalized itinerary..."):
            planning_prompt = (
                f"Based on the following data, create a {num_days}-day itinerary for a {travel_theme.lower()} trip to {destination}. "
                f"The traveler enjoys: {activity_preferences}. Budget: {budget}. Flight Class: {flight_class}. Hotel Rating: {hotel_rating}. "
                f"Visa Requirement: {visa_required}. Travel Insurance: {travel_insurance}. Research: {research_results.content}. "
                f"Flights: {json.dumps(cheapest_flights)}. Hotels & Restaurants: {hotel_restaurant_results.content}. "
                f"Please format the itinerary with clear day headers like 'Day 1:', 'Day 2:', etc. and include specific times for activities."
            )
            itinerary = planner.run(planning_prompt, stream=False)
            st.session_state.itinerary_content = itinerary.content

        # Critic feedback
        # with st.spinner("🧠 Reviewing itinerary..."):
        #     critic_feedback = critic.run(f"Review this itinerary:\n\n{itinerary.content}", stream=False)
        #     st.session_state.critic_feedback = critic_feedback.content

        # Store other session data
        st.session_state.travel_theme = travel_theme
        st.session_state.destination = destination
        st.session_state.departure_date = departure_date
        st.session_state.return_date = return_date
        st.session_state.itinerary_generated = True

        st.success("✅ Travel plan generated successfully!")

    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")
        st.error("Please check your API keys and internet connection.")

# Display results if itinerary has been generated
if st.session_state.itinerary_generated:
    # Display Flights
    st.subheader("✈️ Cheapest Flight Options")
    if st.session_state.cheapest_flights:
        cols = st.columns(len(st.session_state.cheapest_flights))
        for idx, flight in enumerate(st.session_state.cheapest_flights):
            with cols[idx]:
                airline_logo = flight.get("airline_logo", "")
                # airline_name = flight.get("airline_name", "Unknown Airline")
                price = flight.get("price", "Not Available")
                total_duration = flight.get("total_duration", "N/A")
                flights_info = flight.get("flights", [{}])
                departure = flights_info[0].get("departure_airport", {})
                arrival = flights_info[-1].get("arrival_airport", {})
                departure_time = format_datetime(departure.get("time", "N/A"))
                arrival_time = format_datetime(arrival.get("time", "N/A"))
                booking_link = "https://www.google.com/travel/flights"

                st.markdown(
                    f"""
                    <div style="
                        border: 2px solid #ddd; 
                        border-radius: 10px; 
                        padding: 15px; 
                        text-align: center;
                        box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
                        background-color: #f9f9f9;
                        margin-bottom: 20px;
                    ">
                        <img src="{airline_logo}" width="100" alt="Flight Logo" />
                        <p><strong>Departure:</strong> {departure_time}</p>
                        <p><strong>Arrival:</strong> {arrival_time}</p>
                        <p><strong>Duration:</strong> {total_duration} min</p>
                        <h2 style="color: #008000;">💰 {price}</h2>
                        <a href="{booking_link}" target="_blank" style="
                            display: inline-block;
                            padding: 10px 20px;
                            font-size: 16px;
                            font-weight: bold;
                            color: #fff;
                            background-color: #007bff;
                            text-decoration: none;
                            border-radius: 5px;
                            margin-top: 10px;
                        ">🔗 Book Now</a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.warning("⚠️ No flight data available.")

    st.subheader("🏨 Hotels & Restaurants")
    st.write(st.session_state.hotel_restaurant_content)

    st.subheader("🗺️ Your Personalized Itinerary")
    st.write(st.session_state.itinerary_content)

    # st.subheader("💡 Critic Agent Feedback")
    # st.write(st.session_state.critic_feedback)

    # Debug Section (optional - you can remove this after testing)
    # if st.button("🔍 Debug Itinerary Format"):
    #     st.write("**Itinerary Content:**")
    #     st.text(st.session_state.itinerary_content)
        
    #     lines = st.session_state.itinerary_content.split("\n")
    #     st.write("**Line by Line:**")
    #     for i, line in enumerate(lines):
    #         if line.strip():
    #             st.write(f"{i}: `{line}`")

    # Additional Services Section
    st.markdown("---")
    st.subheader("📅 Additional Services")
    
    user_email = st.text_input("Enter your email to receive the itinerary:", value="", key="email_input")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📅 Add to Google Calendar", key="calendar_button"):
            st.warning("Google Calendar and Email features are disabled in this deployed environment due to Oauth security issues.")
            # handle_calendar_integration()
    
    
    with col2:
        if st.button("📧 Send Email", key="email_button"):
            st.warning("Google Calendar and Email features are disabled in this deployed environment due to Oauth security issues.")
            # if user_email:
            #     _, gmail_service = setup_google_services()
            #     if gmail_service:
            #         with st.spinner("📧 Sending email..."):
            #             email_html = f"""
            #             <h2>Your {st.session_state.travel_theme} Trip to {st.session_state.destination}</h2>
            #             <p><strong>Dates:</strong> {st.session_state.departure_date} to {st.session_state.return_date}</p>
            #             <hr />
            #             <h3>Itinerary:</h3>
            #             <pre style="white-space: pre-wrap;">{st.session_state.itinerary_content}</pre>
            #             <hr />
            #             <h3>Hotels & Restaurants:</h3>
            #             <pre style="white-space: pre-wrap;">{st.session_state.hotel_restaurant_content}</pre>
            #             <hr />
            #             <h3>Critic Feedback:</h3>
            #             <pre style="white-space: pre-wrap;">{st.session_state.critic_feedback}</pre>
            #             """
            #             success = send_email_itinerary(gmail_service, f"Travel Itinerary: {st.session_state.destination}", email_html, user_email)
            #             if success:
            #                 st.success("✅ Email sent successfully!")
            #             else:
            #                 st.error("❌ Failed to send email. Please try again.")
            #     else:
            #         st.error("❌ Could not connect to Gmail. Please check your credentials.")
            # else:
            #     st.warning("⚠️ Please enter your email address first.")

    # Clear session button
    if st.button("🔄 Generate New Plan", key="clear_session"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()