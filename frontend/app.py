# frontend/app.py
import streamlit as st
import httpx
from datetime import datetime

# ==================== CONFIG ====================
st.set_page_config(
    page_title="ReplyPilot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "https://replypilot-ozxu.onrender.com"



# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Mono:wght@400;500&display=swap');
    * { font-family: 'DM Sans', sans-serif; }
    .main-header { font-size: 2rem; font-weight: 700; color: #0f172a; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.1rem; color: #64748b; margin-bottom: 2rem; }
    .sentiment-positive { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .sentiment-negative { background: #fef2f2; color: #991b1b; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .sentiment-neutral  { background: #f1f5f9; color: #475569; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .sentiment-mixed    { background: #fef9c3; color: #854d0e; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .urgent-badge { background: #fef2f2; color: #dc2626; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; border: 1px solid #fecaca; }
    .theme-tag { background: #eff6ff; color: #1d4ed8; padding: 3px 10px; border-radius: 14px; font-size: 0.7rem; margin: 2px; display: inline-block; }
    .ai-response-box { background: #f0fdf4; color: #1a1a1a !important; border: 1px solid #bbf7d0; border-left: 4px solid #16a34a; border-radius: 8px; padding: 1rem 1.25rem; margin-top: 0.75rem; font-size: 0.95rem; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)


# ==================== SESSION STATE ====================
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_business" not in st.session_state:
    st.session_state.selected_business = None


# ==================== API HELPERS ====================
def api_headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


def api_get(path, params=None):
    try:
        resp = httpx.get(f"{API_BASE}{path}", headers=api_headers(), params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            st.session_state.token = None
            st.rerun()
        else:
            st.error(f"Error {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None


def api_post(path, data=None, timeout=60):
    try:
        resp = httpx.post(f"{API_BASE}{path}", headers=api_headers(), json=data, timeout=timeout)
        if resp.status_code in (200, 201):
            return resp.json()
        else:
            st.error(f"Error {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None


# ==================== AUTH SCREEN ====================
def show_login():
    st.markdown('<div class="main-header">ReplyPilot</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-powered reputation management for local businesses</div>', unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)
            if submitted and email and password:
                result = api_post("/api/auth/login", {"email": email, "password": password})
                if result:
                    st.session_state.token = result["access_token"]
                    st.session_state.user = result["user"]
                    st.rerun()

    with tab_register:
        with st.form("register_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)
            if submitted and name and email and password:
                result = api_post("/api/auth/register", {
                    "email": email, "password": password, "full_name": name,
                })
                if result:
                    st.session_state.token = result["access_token"]
                    st.session_state.user = result["user"]
                    st.success("Account created!")
                    st.rerun()


# ==================== EMPTY STATE ====================
def show_empty_state():
    st.markdown("## Welcome to ReplyPilot")
    st.write("Add your first business using the sidebar to get started.")
    st.info("Tip: Search for your business on Google Maps and copy the URL.")


# ==================== MAIN APP ====================
def main_app():
    with st.sidebar:
        st.markdown("### ReplyPilot")
        st.caption(f"Signed in as {st.session_state.user.get('email', '')}")

        businesses = api_get("/api/businesses")
        if businesses:
            biz_names = {b["name"]: b for b in businesses}
            if biz_names:
                selected_name = st.selectbox("Select Business", options=list(biz_names.keys()))
                st.session_state.selected_business = biz_names[selected_name]
            else:
                st.session_state.selected_business = None
        else:
            st.session_state.selected_business = None

        st.divider()

        with st.expander("Add New Business"):
            with st.form("add_business"):
                biz_name = st.text_input("Business Name")
                maps_url = st.text_input("Google Maps URL (optional)")
                industry = st.selectbox("Industry", [
                    "restaurant", "dental", "salon", "plumbing",
                    "auto_shop", "hotel", "fitness", "retail",
                    "real_estate", "consulting", "general",
                ])
                submitted = st.form_submit_button("Add Business", use_container_width=True)
                if submitted and biz_name:
                    result = api_post("/api/businesses", {
                        "name": biz_name,
                        "google_maps_url": maps_url if maps_url else None,
                        "industry": industry,
                    })
                    if result:
                        st.success(f"Added {biz_name}!")
                        st.rerun()

        st.divider()

        if st.button("Sign Out", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.selected_business = None
            st.rerun()

    if not st.session_state.selected_business:
        show_empty_state()
        return

    biz = st.session_state.selected_business
    biz_id = biz["id"]

    tab_dash, tab_reviews, tab_activity = st.tabs(["Dashboard", "Reviews", "AI Activity"])

    with tab_dash:
        show_dashboard(biz_id)
    with tab_reviews:
        show_reviews(biz_id)
    with tab_activity:
        show_activity(biz_id)


# ==================== DASHBOARD ====================
def show_dashboard(biz_id):
    data = api_get(f"/api/businesses/{biz_id}/dashboard")
    if not data:
        st.warning("Could not load dashboard. Try fetching reviews first.")
        return

    stats = data.get("stats", {})
    biz = data.get("business", {})
    total = stats.get("total_reviews", 0)

    st.markdown(f'<div class="main-header">{biz.get("name", "Business")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">{biz.get("industry", "").replace("_", " ").title()} - AI Reputation Management</div>', unsafe_allow_html=True)

    if st.button("Fetch New Reviews", type="primary"):
        with st.spinner("Fetching and analyzing reviews with AI..."):
            result = api_post(f"/api/businesses/{biz_id}/fetch-reviews")
            if result:
                new_count = result.get("fetch_result", {}).get("new_reviews", 0)
                analyzed = result.get("analyzed", 0)
                st.success(f"Found {new_count} new reviews. AI analyzed {analyzed} reviews.")
                st.rerun()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Reviews", total)
    with col2:
        st.metric("Average Rating", stats.get("average_rating", 0))
    with col3:
        st.metric("Urgent", stats.get("urgent_count", 0))
    with col4:
        st.metric("AI Response Rate", f"{stats.get('response_rate', 0)}%")

    col5, col6 = st.columns(2)
    with col5:
        st.metric("AI Operations", data.get("ai_operations_count", 0))
    with col6:
        st.metric("Time Saved", f"{data.get('time_saved_minutes', 0)} min")

    st.divider()

    col_dist, col_sent = st.columns(2)
    with col_dist:
        st.subheader("Rating Distribution")
        dist = stats.get("rating_distribution", {})
        for rating in [5, 4, 3, 2, 1]:
            count = dist.get(str(rating), dist.get(rating, 0))
            pct = (count / total * 100) if total > 0 else 0
            st.write(f"{'*' * rating} — {count} ({pct:.0f}%)")
            st.progress(pct / 100 if pct > 0 else 0)
    with col_sent:
        st.subheader("Sentiment Breakdown")
        sentiments = stats.get("sentiment_breakdown", {})
        for sent, count in sorted(sentiments.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total * 100) if total > 0 else 0
            label = {"positive": "Positive", "negative": "Negative",
                     "neutral": "Neutral", "mixed": "Mixed"}.get(sent, sent)
            st.write(f"{label}: {count} ({pct:.0f}%)")

    st.divider()

    st.subheader("Recent Reviews")
    recent = data.get("recent_reviews", [])
    if not recent:
        st.info("No reviews yet. Click 'Fetch New Reviews' to get started.")
    else:
        for i, review in enumerate(recent):
            render_review_card(review, biz_id, compact=True, prefix=f"dash_{i}")

    alerts = data.get("unread_alerts", [])
    if alerts:
        st.divider()
        st.subheader("Unread Alerts")
        for alert in alerts:
            st.warning(f"**{alert['title']}** - {alert['message']}")


# ==================== REVIEWS ====================
def show_reviews(biz_id):
    st.subheader("All Reviews")

    col1, col2, col3 = st.columns(3)
    with col1:
        sentiment_filter = st.selectbox("Sentiment", ["All", "positive", "negative", "neutral", "mixed"])
    with col2:
        rating_filter = st.selectbox("Rating", ["All", "5", "4", "3", "2", "1"])
    with col3:
        urgent_filter = st.checkbox("Urgent only")

    params = {}
    if sentiment_filter != "All":
        params["sentiment"] = sentiment_filter
    if rating_filter != "All":
        params["min_rating"] = int(rating_filter)
        params["max_rating"] = int(rating_filter)
    if urgent_filter:
        params["urgent_only"] = True

    reviews = api_get(f"/api/businesses/{biz_id}/reviews", params=params)
    if not reviews:
        st.info("No reviews match your filters.")
        return

    st.write(f"Showing {len(reviews)} reviews")
    for i, review in enumerate(reviews):
        render_review_card(review, biz_id, compact=False, prefix=f"rev_{i}")


# ==================== REVIEW CARD ====================
def render_review_card(review, biz_id, compact=False, prefix=""):
    sentiment = review.get("ai_sentiment", "unknown")
    rating = review.get("rating", 0)
    is_urgent = review.get("ai_is_urgent", False)

    with st.container():
        col_main, col_actions = st.columns([4, 1])

        with col_main:
            name = review.get("reviewer_name", "Anonymous")
            date_str = ""
            if review.get("review_date"):
                try:
                    date_str = str(review["review_date"])[:10]
                except:
                    pass

            stars = "*" * rating
            badges = f'<span class="sentiment-{sentiment}">{sentiment}</span>'
            if is_urgent:
                badges += ' <span class="urgent-badge">URGENT</span>'

            st.markdown(f"**{name}** | {stars} | {date_str} {badges}", unsafe_allow_html=True)

            text = review.get("review_text", "")
            if text:
                if compact and len(text) > 200:
                    st.write(text[:200] + "...")
                else:
                    st.write(text)

            if review.get("ai_summary") and not compact:
                st.caption(f"AI Summary: {review['ai_summary']}")

            themes = review.get("ai_themes", [])
            if themes:
                tags = " ".join([f'<span class="theme-tag">{t.replace("_", " ")}</span>' for t in themes])
                st.markdown(tags, unsafe_allow_html=True)

            if review.get("latest_ai_response"):
                st.markdown(
                    f'<div class="ai-response-box"><strong>AI Response:</strong><br>{review["latest_ai_response"]}</div>',
                    unsafe_allow_html=True,
                )

        with col_actions:
            if not review.get("has_ai_response"):
                if st.button("Generate", key=f"gen_{prefix}_{review['id']}", use_container_width=True):
                    with st.spinner("AI writing response..."):
                        result = api_post(f"/api/reviews/{review['id']}/generate-response")
                        if result:
                            st.success("Response generated!")
                            st.rerun()
            else:
                status = review.get("ai_response_status", "draft")
                if status == "draft":
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("Approve", key=f"ap_{prefix}_{review['id']}", use_container_width=True):
                            responses = api_get(f"/api/reviews/{review['id']}/responses")
                            if responses:
                                api_post(f"/api/responses/{responses[0]['id']}/approve")
                                st.success("Approved!")
                                st.rerun()
                    with col_b:
                        if st.button("Redo", key=f"re_{prefix}_{review['id']}", use_container_width=True):
                            with st.spinner("Regenerating..."):
                                api_post(f"/api/reviews/{review['id']}/generate-response")
                                st.rerun()
                elif status == "approved":
                    st.success("Approved")

        st.divider()


# ==================== ACTIVITY LOG ====================
def show_activity(biz_id):
    st.subheader("AI Activity Log")
    st.write("Every AI operation is logged here.")

    activity = api_get(f"/api/businesses/{biz_id}/activity")
    if not activity:
        st.info("No AI activity yet.")
        return

    for item in activity:
        action = item.get("action", "unknown")
        actor = item.get("actor", "system")
        details = item.get("details", {})
        processing_time = item.get("processing_time_ms")
        created = item.get("created_at", "")

        time_str = ""
        try:
            time_str = created[:16].replace("T", " ")
        except:
            time_str = created

        actor_label = "AI" if actor == "ai" else "You" if actor == "user" else "System"

        detail_str = ""
        if action == "review_analyzed" and details:
            detail_str = f"Sentiment: {details.get('sentiment', '?')}, Themes: {', '.join(details.get('themes', []))}"
        elif action == "response_generated" and details:
            detail_str = f"Response for {details.get('rating', '?')}-star review ({details.get('response_length', '?')} chars)"
        elif action == "reviews_fetched" and details:
            detail_str = f"{details.get('new', 0)} new reviews, {details.get('duplicates_skipped', 0)} duplicates skipped"

        time_note = f" | {processing_time}ms" if processing_time else ""

        st.markdown(f"**{action.replace('_', ' ').title()}** by {actor_label}")
        if detail_str:
            st.caption(f"    {detail_str}{time_note} | {time_str}")
        else:
            st.caption(f"    {time_str}{time_note}")


# ==================== RUN ====================
if st.session_state.token:
    main_app()
else:
    show_login()
