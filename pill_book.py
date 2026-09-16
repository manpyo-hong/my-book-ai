import streamlit as st
import requests
from datetime import date
import uuid

# 페이지 설정
st.set_page_config(
    page_title="나만의 복용 기록부",
    page_icon="💊",
    layout="centered"
)

# 🎨 디자인 및 배지 스타일 CSS
st.markdown("""
    <style>
    .main {
        background-color: #f8fafc;
    }
    h1 {
        color: #1e293b;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    h3 {
        color: #334155;
        font-weight: 700;
    }
    .stHorizontalBlock {
        align-items: center;
    }
    /* 시간대 배지 스타일 */
    .badge-time {
        background-color: #e0f2fe;
        color: #0284c7;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 4px;
    }
    /* 용량 비교 배지 스타일 */
    .badge-dosage {
        background-color: #f1f5f9;
        color: #475569;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 500;
        margin-right: 4px;
    }
    /* 미니 삭제 버튼 커스텀 */
    div[data-testid="column"] button {
        padding: 2px 8px !important;
        font-size: 0.75rem !important;
        min-height: unset !important;
        height: 30px !important;
        background-color: #f1f5f9;
        color: #64748b;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
    }
    div[data-testid="column"] button:hover {
        background-color: #fee2e2;
        color: #dc2626;
        border-color: #fca5a5;
    }
    </style>
""", unsafe_allow_html=True)

TIME_SLOTS = ["아침", "점심", "저녁", "취침 전"]


# ---------------- 구글 앱스 스크립트 연동 ----------------
def sheets_enabled() -> bool:
    return "APPS_SCRIPT_URL" in st.secrets and "APPS_SCRIPT_SECRET" in st.secrets


def call_apps_script(action, data=None):
    url = st.secrets["APPS_SCRIPT_URL"]
    payload = {
        "action": action,
        "secret": st.secrets["APPS_SCRIPT_SECRET"]
    }
    if data:
        payload.update(data)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        res_json = response.json()
        if not res_json.get("success"):
            raise Exception(res_json.get("error", "알 수 없는 에러"))
        return res_json.get("data")
    except Exception as e:
        raise Exception(f"앱스 스크립트 통신 오류: {e}")


def load_supplements_from_sheet():
    rows = call_apps_script("get_all")
    supplements = []
    if not rows:
        return []

    for r in rows:
        if not r.get("id"):
            continue
        
        raw_date = str(r.get("start_date", ""))
        clean_date = raw_date[:10] if len(raw_date) >= 10 else raw_date

        supplements.append({
            "id": r["id"],
            "name": r.get("name", ""),
            "dosage": r.get("dosage", ""),
            "start_date": clean_date,
            "eat_time": r.get("eat_time", ""),
        })
    return supplements


def append_supplement_to_sheet(item):
    call_apps_script("add", {
        "id": item["id"],
        "name": item["name"],
        "dosage": item["dosage"],
        "start_date": item["start_date"],
        "eat_time": item["eat_time"]
    })


def delete_supplement_from_sheet(item_id):
    call_apps_script("delete", {"id": item_id})


def ai_lookup(name: str) -> str:
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY가 설정되지 않았습니다.")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    
    prompt = f"""
    당신은 전문 약사입니다. 다음 약 또는 영양제에 대해 알려주세요: {name}
    효능/효과, 권장 복용 방법(1일 권장 용량 포함), 주의사항을 포함하여 간결하고 명확하게 마크다운 형식으로 정리해 주세요.
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    response = requests.post(url, json=payload, timeout=30)
    res_json = response.json()
    
    if "error" in res_json:
        raise Exception(res_json["error"].get("message", "AI 응답 오류"))
        
    try:
        return res_json["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        raise Exception("AI 응답을 파싱하는 중 오류가 발생했습니다.")


# 세션 상태 초기화
if "supplements" not in st.session_state:
    st.session_state.supplements = []
    if sheets_enabled():
        try:
            with st.spinner("구글 시트에서 데이터를 불러오는 중입니다..."):
                st.session_state.supplements = load_supplements_from_sheet()
            st.session_state.sheet_error = None
        except Exception as e:
            st.session_state.sheet_error = str(e)
    else:
        st.session_state.sheet_error = "not_configured"


# 메인 타이틀
st.title("💊 스마트 복용 기록부")
st.markdown("처방약과 영양제를 스마트하게 관리하고 기록하세요.")

with st.expander("💡 이용 안내 및 주의사항", expanded=False):
    st.info(
        "이 정보는 AI가 조회한 참고용 자료이며 부정확하거나 최신이 아닐 수 있습니다. "
        "실제 복용 여부와 병용 가능 여부는 반드시 약사 또는 의사와 상담한 뒤 결정하세요."
    )

st.write("")
tab1, tab2 = st.tabs(["📋 처방약 검색", "🌿 영양제 관리"])

# ---------------- 처방약 탭 ----------------
with tab1:
    st.markdown("### 처방약 성분 및 효능 조회")
    col1, col2, col3 = st.columns([3, 1, 1], vertical_alignment="bottom")
    with col1:
        drug_input = st.text_input("약 이름 입력", placeholder="예: 타이레놀, 아목시실린", label_visibility="collapsed", key="drug_name_input")
    with col2:
        ai_search = st.button("✨ AI 조회", use_container_width=True, key="drug_ai_search", type="primary")
    with col3:
        direct_input = st.button("➕ 직접 입력", use_container_width=True, key="drug_direct_input")

    if ai_search:
        if not drug_input.strip():
            st.warning("검색할 약 이름을 입력해주세요.")
        else:
            with st.spinner(f"'{drug_input}'에 대한 정보를 분석 중입니다..."):
                try:
                    ai_result = ai_lookup(drug_input)
                    st.success(f"'{drug_input}' AI 분석 완료!")
                    with st.container(border=True):
                        st.markdown(ai_result)
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

# ---------------- 영양제 탭 ----------------
with tab2:
    if st.session_state.get("sheet_error") == "not_configured":
        st.info("ℹ️ 구글 시트 연동이 설정되지 않아 브라우저 세션에만 임시로 저장됩니다.")
    elif st.session_state.get("sheet_error"):
        st.error(f"⚠️ 구글 시트 연결 실패: {st.session_state['sheet_error']}")

    st.markdown("### 영양제 추가하기")

    col1, col2, col3 = st.columns([3, 1, 1], vertical_alignment="bottom")
    with col1:
        supp_input = st.text_input("영양제 이름 입력", placeholder="예: 오메가3 프리미엄", label_visibility="collapsed", key="supp_name_input")
    with col2:
        supp_ai_search = st.button("✨ AI 조회", use_container_width=True, key="supp_ai_search", type="primary")
    with col3:
        supp_direct_input = st.button("➕ 직접 등록", use_container_width=True, key="supp_direct_input")

    if supp_ai_search:
        if not supp_input.strip():
            st.warning("검색할 영양제 이름을 입력해주세요.")
        else:
            with st.spinner(f"'{supp_input}'에 대한 정보를 분석 중입니다..."):
                try:
                    st.session_state["supp_ai_result"] = ai_lookup(supp_input)
                    st.session_state["supp_ai_result_name"] = supp_input
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

    if st.session_state.get("supp_ai_result"):
        with st.container(border=True):
            st.markdown(f"#### 💊 {st.session_state['supp_ai_result_name']} AI 정보 (권장 용량 확인)")
            st.markdown(st.session_state["supp_ai_result"])

    show_form = supp_direct_input or bool(st.session_state.get("supp_ai_result"))

    if show_form:
        with st.form("add_supplement_form", clear_on_submit=True):
            st.markdown("#### 📝 복용 정보 입력")
            f_name = st.text_input("영양제 이름", value=supp_input if supp_input else "")
            
            # 입력 편의를 위해 권장 용량과 1정 용량을 구분해서 입력받도록 구성
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                f_recommended = st.text_input("1일 권장 용량", placeholder="예: 1일 2정 또는 1000mg", value="")
            with col_f2:
                f_dosage = st.text_input("등록된 영양제 1정 용량", placeholder="예: 1정, 2캡슐", value="")
                
            f_eat_times = st.multiselect("먹는 시간 선택", TIME_SLOTS, default=["점심"])
            
            submitted = st.form_submit_button("저장하기", type="primary", use_container_width=True)

            if submitted:
                if not f_name.strip():
                    st.error("영양제 이름을 입력해주세요.")
                else:
                    eat_time_str = ", ".join(f_eat_times) if f_eat_times else "점심"
                    # 권장 용량과 1정 용량을 보기 좋게 합쳐서 dosage 칸에 저장
                    combined_dosage = f"권장: {f_recommended.strip()} | 1정: {f_dosage.strip()}" if f_recommended.strip() else (f_dosage.strip() or "섭취량 미입력")
                    
                    new_item = {
                        "id": str(uuid.uuid4()),
                        "name": f_name.strip(),
                        "dosage": combined_dosage,
                        "start_date": date.today().isoformat(),
                        "eat_time": eat_time_str,
                    }
                    if sheets_enabled() and not st.session_state.get("sheet_error"):
                        try:
                            append_supplement_to_sheet(new_item)
                        except Exception as e:
                            st.error(f"구글 시트 저장 실패: {e}")
                    st.session_state.supplements.append(new_item)
                    st.session_state.pop("supp_ai_result", None)
                    st.session_state.pop("supp_ai_result_name", None)
                    st.success(f"'{f_name}'이(가) 성공적으로 추가되었습니다!")
                    st.rerun()

    st.divider()
    st.markdown("### 📋 복용 중인 영양제 목록")

    if not st.session_state.supplements:
        st.info("아직 등록된 영양제가 없습니다. 위에서 영양제를 추가해보세요.")
    else:
        for item in st.session_state.supplements:
            with st.container(border=True):
                c_info, c_btn = st.columns([9, 1])
                with c_info:
                    st.markdown(
                        f"**{item['name']}** &nbsp; "
                        f"<span class='badge-time'>🕒 {item.get('eat_time', '점심')}</span>"
                        f"<span class='badge-dosage'>💊 {item['dosage']}</span>"
                        f"<span style='color: #94a3b8; font-size: 0.75rem; margin-left: 6px;'>({item['start_date']})</span>",
                        unsafe_allow_html=True
                    )
                with c_btn:
                    if st.button("삭제", key=f"delete_{item['id']}", use_container_width=True):
                        if sheets_enabled() and not st.session_state.get("sheet_error"):
                            try:
                                delete_supplement_from_sheet(item["id"])
                            except Exception as e:
                                st.error(f"구글 시트 삭제 실패: {e}")
                        st.session_state.supplements = [
                            s for s in st.session_state.supplements if s["id"] != item["id"]
                        ]
                        st.rerun()
