import os
import random
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from dotenv import load_dotenv

load_dotenv()
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

st.set_page_config(page_title="어디갈까? 장소 검색 지도", page_icon="🧭", layout="wide")

st.markdown("""
<style>
    .main .block-container {
        padding-top: 1.5rem;
        max-width: 1200px;
    }
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        text-align: center;
        margin-top: 0.5rem;
        margin-bottom: 0.2rem;
        background: linear-gradient(90deg, #FF6B35, #F7B32B);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        text-align: center;
        font-size: 1.15rem;
        color: #888;
        margin-bottom: 1.2rem;
    }
    .loc-badge {
        text-align: center;
        color: #4CB963;
        font-size: 0.85rem;
        margin-bottom: 0.6rem;
    }
</style>
""", unsafe_allow_html=True)

if not KAKAO_REST_API_KEY:
    st.error(".env 파일에 KAKAO_REST_API_KEY가 설정되어 있지 않습니다.")
    st.stop()


def search_place(keyword: str, user_lat=None, user_lng=None):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query": keyword}

    if user_lat is not None and user_lng is not None:
        params["x"] = user_lng
        params["y"] = user_lat
        params["sort"] = "distance"

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json().get("documents", [])


def format_distance(distance_str):
    if not distance_str:
        return None
    try:
        meters = int(distance_str)
    except ValueError:
        return None
    if meters == 0:
        return None
    if meters < 1000:
        return f"{meters}m"
    return f"{meters / 1000:.1f}km"


def get_roadview_url(lat, lng):
    return f"https://map.kakao.com/link/roadview/{lat},{lng}"


def get_marker_emoji_color(place_name, category_name):
    name = place_name.replace(" ", "").lower()
    brand_styles = {
        "스타벅스": ("☕", "green"),
        "starbucks": ("☕", "green"),
        "이디야": ("☕", "blue"),
        "투썸플레이스": ("☕", "darkred"),
        "메가커피": ("☕", "orange"),
        "맥도날드": ("🍔", "red"),
        "버거킹": ("🍔", "darkred"),
        "롯데리아": ("🍔", "red"),
        "cu": ("🏪", "purple"),
        "gs25": ("🏪", "blue"),
        "세븐일레븐": ("🏪", "orange"),
        "올리브영": ("🧴", "lightgreen"),
    }
    for kw, (emoji, color) in brand_styles.items():
        if kw in name:
            return emoji, color
    if "카페" in category_name:
        return "☕", "cadetblue"
    if "음식점" in category_name:
        return "🍽️", "orange"
    if "편의점" in category_name:
        return "🏪", "gray"
    return "📍", "blue"


def render_place_card(i, place, key_prefix=""):
    name = place["place_name"]
    lat = float(place["y"])
    lng = float(place["x"])
    address = place.get("road_address_name") or place.get("address_name")
    category_name = place.get("category_name", "")
    emoji, _ = get_marker_emoji_color(name, category_name)
    dist_label = format_distance(place.get("distance"))
    roadview_url = get_roadview_url(lat, lng)
    place_url = place.get("place_url")

    with st.container(border=True):
        title_col, dist_col = st.columns([4, 1])
        with title_col:
            st.markdown(f"**{i}. {emoji} {name}**")
        with dist_col:
            if dist_label:
                st.caption(f"📍 {dist_label}")
        st.caption(address)

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            st.link_button("🚶 로드뷰", roadview_url, use_container_width=True, key=f"{key_prefix}rv_{i}")
        with btn_col2:
            if place_url:
                st.link_button("⭐ 평점/후기", place_url, use_container_width=True, key=f"{key_prefix}rt_{i}")
            else:
                st.button("⭐ 정보없음", disabled=True, use_container_width=True, key=f"{key_prefix}none_{i}")


def build_map(results, user_lat=None, user_lng=None):
    if user_lat is not None:
        center_lat, center_lng = user_lat, user_lng
    else:
        center_lat = float(results[0]["y"])
        center_lng = float(results[0]["x"])

    m = folium.Map(location=[center_lat, center_lng], zoom_start=15, tiles="OpenStreetMap")

    if user_lat is not None:
        folium.Marker(
            location=[user_lat, user_lng],
            popup="내 위치",
            tooltip="📍 내 위치",
            icon=folium.Icon(color="black", icon="user", prefix="fa"),
        ).add_to(m)

    for place in results:
        name = place["place_name"]
        lat = float(place["y"])
        lng = float(place["x"])
        address = place.get("road_address_name") or place.get("address_name")
        category_name = place.get("category_name", "")
        emoji, color = get_marker_emoji_color(name, category_name)
        dist_label = format_distance(place.get("distance"))
        roadview_url = get_roadview_url(lat, lng)
        place_url = place.get("place_url")

        popup_lines = [f"<b>{emoji} {name}</b>", address]
        if dist_label:
            popup_lines.append(f"내 위치에서 {dist_label}")
        popup_lines.append(f'<a href="{roadview_url}" target="_blank">🚶 로드뷰 보기</a>')
        if place_url:
            popup_lines.append(f'<a href="{place_url}" target="_blank">⭐ 평점/후기</a>')
        else:
            popup_lines.append("평점 정보 없음")
        popup_html = "<br>".join(popup_lines)

        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{emoji} {name}" + (f" · {dist_label}" if dist_label else ""),
            icon=folium.Icon(color=color, icon="info-sign"),
        ).add_to(m)

    return m


HERO_SVG = """<div style="text-align:center; margin-bottom: -1.2rem;">
<svg width="260" height="200" viewBox="0 0 260 200" xmlns="http://www.w3.org/2000/svg">
<ellipse cx="130" cy="185" rx="90" ry="10" fill="#F3E9DC"/>
<rect x="40" y="140" width="180" height="10" rx="3" fill="#D9B48F"/>
<rect x="55" y="150" width="8" height="30" fill="#C9A47A"/>
<rect x="197" y="150" width="8" height="30" fill="#C9A47A"/>
<rect x="95" y="80" width="90" height="60" rx="6" fill="#3C3B6E"/>
<rect x="102" y="87" width="76" height="46" rx="3" fill="#EAF4FF"/>
<rect x="128" y="140" width="14" height="12" fill="#B0B0B0"/>
<rect x="115" y="151" width="40" height="6" rx="2" fill="#9C9C9C"/>
<circle cx="140" cy="110" r="16" fill="#CFE8CF"/>
<path d="M124 110c0-9 7-16 16-16s16 7 16 16-16 24-16 24-16-15-16-24z" fill="#FF6B35"/>
<circle cx="140" cy="108" r="5" fill="white"/>
<circle cx="75" cy="100" r="16" fill="#FFD6B8"/>
<path d="M50 150c0-18 12-32 25-32s25 14 25 32z" fill="#FF6B35"/>
<path d="M70 118c-8 4-14 12-16 20" stroke="#FFD6B8" stroke-width="7" stroke-linecap="round" fill="none"/>
<path d="M84 118c6 4 10 10 12 16" stroke="#FFD6B8" stroke-width="7" stroke-linecap="round" fill="none"/>
<circle cx="205" cy="55" r="14" fill="none" stroke="#F7B32B" stroke-width="5"/>
<line x1="215" y1="65" x2="228" y2="78" stroke="#F7B32B" stroke-width="5" stroke-linecap="round"/>
<path d="M40 60c0-7 5-12 12-12s12 5 12 12-12 18-12 18-12-11-12-18z" fill="#4CB963" opacity="0.85"/>
<circle cx="52" cy="59" r="4" fill="white"/>
</svg>
</div>"""

if "page" not in st.session_state:
    st.session_state.page = "home"
if "search_keyword" not in st.session_state:
    st.session_state.search_keyword = ""
if "food_keyword" not in st.session_state:
    st.session_state.food_keyword = ""


def go_home():
    st.session_state.page = "home"


location = get_geolocation()
user_lat, user_lng = None, None
if location and "coords" in location:
    user_lat = location["coords"]["latitude"]
    user_lng = location["coords"]["longitude"]

if st.session_state.page == "home":
    st.markdown(HERO_SVG, unsafe_allow_html=True)
    st.markdown('<div class="hero-title">🧭 어디 갈까?</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">가고 싶은 곳을 자유롭게 검색해보세요!!</div>', unsafe_allow_html=True)

    if user_lat is not None:
        st.markdown('<div class="loc-badge">📍 내 위치를 기준으로 거리를 계산하고 있어요</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="loc-badge" style="color:#bbb;">위치 권한을 허용하면 내 주변 거리(m)를 함께 보여드려요</div>',
            unsafe_allow_html=True,
        )

    _, center_col, _ = st.columns([1, 3, 1])
    with center_col:
        keyword_input = st.text_input(
            "장소 검색",
            placeholder="예: 강남역 스타벅스, 경복궁, 을지로 맛집 ...",
            label_visibility="collapsed",
            key="home_search_input",
        )
        if st.button("🔍 검색하기", use_container_width=True) and keyword_input.strip():
            st.session_state.search_keyword = keyword_input.strip()
            st.session_state.page = "search"
            st.rerun()

    st.write("")
    st.divider()
    st.markdown("## 🍚 오늘 뭐 먹지?")
    st.caption("주변 맛집을 추천해드려요. 음식 종류나 동네를 적어도 되고, 비워두면 아무거나 골라드려요!")

    food_col1, food_col2 = st.columns([4, 1])
    with food_col1:
        food_keyword_input = st.text_input(
            "밥 뭐먹지 검색",
            placeholder="예: 한식, 파스타, 강남 맛집 ... (비워두면 랜덤 추천)",
            label_visibility="collapsed",
            key="home_food_input",
        )
    with food_col2:
        if st.button("🍽️ 추천받기", use_container_width=True):
            st.session_state.food_keyword = food_keyword_input.strip()
            st.session_state.page = "food"
            st.rerun()

    st.write("")
    tip_col1, tip_col2, tip_col3 = st.columns(3)
    with tip_col1:
        st.markdown("### ☕ 카페")
        st.caption("스타벅스, 이디야, 투썸플레이스처럼 브랜드명으로 검색해보세요")
    with tip_col2:
        st.markdown("### 🍽️ 맛집")
        st.caption("동네 이름 + 맛집으로 검색하면 주변 인기 장소가 쭉 나와요")
    with tip_col3:
        st.markdown("### 🏛️ 명소")
        st.caption("경복궁, N서울타워 같은 관광 명소도 검색 가능해요")

elif st.session_state.page == "search":
    st.button("← 처음으로", on_click=go_home)
    keyword = st.session_state.search_keyword

    results = search_place(keyword, user_lat, user_lng)

    if not results:
        st.warning(f"'{keyword}' 검색 결과가 없습니다.")
    else:
        st.markdown(f"#### '{keyword}' 검색 결과 **{len(results)}건**")
        st.write("")

        m = build_map(results, user_lat, user_lng)

        map_col, list_col = st.columns([3, 2], gap="large")

        with map_col:
            st.markdown("**🗺️ 지도** (마커를 클릭하면 로드뷰·평점 링크가 떠요)")
            st_folium(m, width=None, height=620, use_container_width=True)

        with list_col:
            st.markdown("**📋 결과 & 평점/후기**")
            list_area = st.container(height=620)
            with list_area:
                for i, place in enumerate(results, start=1):
                    render_place_card(i, place, key_prefix="main_")

elif st.session_state.page == "food":
    st.button("← 처음으로", on_click=go_home)

    query = st.session_state.food_keyword if st.session_state.food_keyword else "맛집"
    st.markdown(f"## 🍚 오늘 뭐 먹지? — '{query}' 기준")

    food_results = search_place(query, user_lat, user_lng)

    if not food_results:
        st.warning("추천할 만한 곳을 못 찾았어요. 처음으로 돌아가서 다른 키워드로 시도해보세요.")
    else:
        pick = random.choice(food_results[: min(10, len(food_results))])
        st.success(f"오늘의 추천: **{pick['place_name']}** 어때요? 🍽️")

        pick_lat = float(pick["y"])
        pick_lng = float(pick["x"])
        pick_address = pick.get("road_address_name") or pick.get("address_name")
        dist_label = format_distance(pick.get("distance"))

        with st.container(border=True):
            st.markdown(f"### 🍽️ {pick['place_name']}")
            st.caption(pick_address + (f" · 내 위치에서 {dist_label}" if dist_label else ""))
            b1, b2 = st.columns(2)
            with b1:
                st.link_button("🚶 로드뷰", get_roadview_url(pick_lat, pick_lng), use_container_width=True)
            with b2:
                if pick.get("place_url"):
                    st.link_button("⭐ 평점/후기", pick["place_url"], use_container_width=True)
                else:
                    st.button("⭐ 정보없음", disabled=True, use_container_width=True)

        st.write("")
        if st.button("🔄 다른 곳 추천받기"):
            st.rerun()

        with st.expander("다른 후보들도 보기"):
            for i, place in enumerate(food_results[:10], start=1):
                if place is pick:
                    continue
                render_place_card(i, place, key_prefix="food_")