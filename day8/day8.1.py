import os
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium
from dotenv import load_dotenv

load_dotenv()
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

st.set_page_config(page_title="어디갈까? 장소 검색 지도", page_icon="🧭", layout="wide")

# ---------- 커스텀 스타일 ----------
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
        margin-bottom: 1.8rem;
    }
    div[data-testid="stTextInput"] input {
        border-radius: 999px !important;
        padding: 0.9rem 1.4rem !important;
        font-size: 1.05rem !important;
        border: 2px solid #eee !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #FF6B35 !important;
        box-shadow: 0 0 0 3px rgba(255,107,53,0.15) !important;
    }
    .place-card {
        border: 1px solid #ececec;
        border-radius: 16px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.9rem;
        background-color: #ffffff;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .place-rank {
        display: inline-block;
        background: #FF6B35;
        color: white;
        font-size: 0.75rem;
        font-weight: 700;
        border-radius: 999px;
        width: 22px;
        height: 22px;
        line-height: 22px;
        text-align: center;
        margin-right: 6px;
    }
    .place-name {
        font-size: 1.05rem;
        font-weight: 700;
        display: inline;
    }
    .place-address {
        color: #999;
        font-size: 0.85rem;
        margin: 0.25rem 0 0.7rem 0;
    }
    .section-label {
        font-size: 0.95rem;
        font-weight: 700;
        color: #555;
        margin-bottom: 0.6rem;
    }
</style>
""", unsafe_allow_html=True)

if not KAKAO_REST_API_KEY:
    st.error(".env 파일에 KAKAO_REST_API_KEY가 설정되어 있지 않습니다.")
    st.stop()


def search_place(keyword: str):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query": keyword}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json().get("documents", [])


def get_roadview_url(lat, lng):
    return f"https://map.kakao.com/link/roadview/{lat},{lng}"


def get_marker_style(place_name, category_name):
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


HERO_SVG = """
<div style="text-align:center; margin-bottom: -1.2rem;">
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
</div>
"""

st.markdown(HERO_SVG, unsafe_allow_html=True)
st.markdown('<div class="hero-title">🧭 어디 갈까?</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">가고 싶은 곳을 자유롭게 검색해보세요!!</div>', unsafe_allow_html=True)

_, center_col, _ = st.columns([1, 3, 1])
with center_col:
    keyword = st.text_input(
        "장소 검색",
        placeholder="예: 강남역 스타벅스, 경복궁, 을지로 맛집 ...",
        label_visibility="collapsed",
    )

st.write("")

if not keyword:
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

else:
    results = search_place(keyword)

    if not results:
        st.warning("검색 결과가 없습니다. 다른 키워드로 시도해보세요.")
    else:
        st.markdown(f"#### '{keyword}' 검색 결과 **{len(results)}건**")
        st.write("")

        center_lat = float(results[0]["y"])
        center_lng = float(results[0]["x"])

        m = folium.Map(location=[center_lat, center_lng], zoom_start=15, tiles="cartodbpositron")

        for place in results:
            name = place["place_name"]
            lat = float(place["y"])
            lng = float(place["x"])
            address = place.get("road_address_name") or place.get("address_name")
            category_name = place.get("category_name", "")
            emoji, color = get_marker_style(name, category_name)

            folium.Marker(
                location=[lat, lng],
                popup=f"{emoji} {name}<br>{address}",
                tooltip=f"{emoji} {name}",
                icon=folium.Icon(color=color, icon="info-sign"),
            ).add_to(m)

        # 지도와 리스트를 좌우로 배치
        map_col, list_col = st.columns([3, 2], gap="large")

        with map_col:
            st.markdown('<div class="section-label">🗺️ 지도</div>', unsafe_allow_html=True)
            st_folium(m, width=None, height=620, use_container_width=True)

        with list_col:
            st.markdown('<div class="section-label">📋 결과 & 평점/후기</div>', unsafe_allow_html=True)
            list_area = st.container(height=620)

        for i, place in enumerate(results, start=1):
            name = place["place_name"]
            lat = float(place["y"])
            lng = float(place["x"])
            address = place.get("road_address_name") or place.get("address_name")
            category_name = place.get("category_name", "")
            emoji, _ = get_marker_style(name, category_name)

            with list_area:
                st.markdown(
                    f"""
                    <div class="place-card">
                        <span class="place-rank">{i}</span>
                        <span class="place-name">{emoji} {name}</span>
                        <div class="place-address">{address}</div>
                    """,
                    unsafe_allow_html=True,
                )

                roadview_url = get_roadview_url(lat, lng)
                place_url = place.get("place_url")

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    st.link_button("🚶 로드뷰", roadview_url, use_container_width=True)
                with btn_col2:
                    if place_url:
                        st.link_button("⭐ 평점/후기", place_url, use_container_width=True)
                    else:
                        st.button("⭐ 정보없음", disabled=True, use_container_width=True, key=f"none_{i}")

                st.markdown("</div>", unsafe_allow_html=True)