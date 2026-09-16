import streamlit as st
import requests
from datetime import date
import uuid

# 페이지 설정
st.set_page_config(
    page_title="복용 기록부",
    page_icon="💊",
    layout="centered"
)

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
        supplements.append({
            "id": r["id"],
            "name": r.get("name", ""),
            "dosage": r.get("dosage", ""),
            "start_date": r.get("start_date", ""),
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
    효능/효과, 권장 복용 방법, 주의사항을 포함하여 간결하고 명확하게 마크다운 형식으로 정리해 주세요.
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
st.title("복용 기록부")
st.write("처방약과 영양제를 한 곳에서 정리하고 확인하세요.")

st.warning(
    "이 정보는 AI가 조회한 참고용 자료이며 부정확하거나 최신이 아닐 수 있습니다. "
    "실제 복용 여부와 병용 가능 여부는 반드시 약사 또는 의사와 상담한 뒤 결정하세요."
)

tab1, tab2 = st.tabs(["처방약", "영양제"])

# ---------------- 처방약 탭 ----------------
with tab1:
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        drug_input = st.text_input("약 이름 입력", placeholder="예: 타이레놀", label_visibility="collapsed", key="drug_name_input")
    with col2:
        ai_search = st.button("Q AI로 조회", use_container_width=True, key="drug_ai_search")
    with col3:
        direct_input = st.button("+ 직접 입력", use_container_width=True, key="drug_direct_input")

    if ai_search:
        if not drug_input.strip():
            st.error("검색할 약 또는 영양제 이름을 입력해주세요.")
        else:
            with st.spinner(f"'{drug_input}'에 대한 정보를 검색 중입니다..."):
                try:
                    ai_result = ai_lookup(drug_input)
                    st.success(f"'{drug_input}'에 대한 AI 검색 결과입니다.")
                    with st.expander(f"💊 {drug_input} 상세 정보 확인하기", expanded=True):
                        st.markdown(ai_result)
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

# ---------------- 영양제 탭 ----------------
with tab2:
    if st.session_state.get("sheet_error") == "not_configured":
        st.info("구글 시트 연동이 설정되지 않아 브라우저 세션에만 임시로 저장됩니다.")
    elif st.session_state.get("sheet_error"):
        st.error(f"⚠️ 구글 시트 연결 실패: {st.session_state['sheet_error']}")

    st.subheader("영양제 등록")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        supp_input = st.text_input("영양제 이름 입력", placeholder="예: 오메가3 프리미엄", label_visibility="collapsed", key="supp_name_input")
    with col2:
        supp_ai_search = st.button("Q AI로 조회", use_container_width=True, key="supp_ai_search")
    with col3:
        supp_direct_input = st.button("+ 직접 입력", use_container_width=True, key="supp_direct_input")

    if supp_ai_search:
        if not supp_input.strip():
            st.error("검색할 영양제 이름을 입력해주세요.")
        else:
            with st.spinner(f"'{supp_input}'에 대한 정보를 검색 중입니다..."):
                try:
                    st.session_state["supp_ai_result"] = ai_lookup(supp_input)
                    st.session_state["supp_ai_result_name"] = supp_input
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

    if st.session_state.get("supp_ai_result"):
        with st.expander(f"💊 {st.session_state['supp_ai_result_name']} 상세 정보 확인하기", expanded=True):
            st.markdown(st.session_state["supp_ai_result"])

    show_form = supp_direct_input or bool(st.session_state.get("supp_ai_result"))

    if show_form:
        with st.form("add_supplement_form", clear_on_submit=True):
            st.write("복용 중인 목록에 추가하기")
            f_name = st.text_input("영양제 이름", value=supp_input if supp_input else "")
            f_dosage = st.text_input("1회 섭취량 (예: 1정, 2캡슐)", value="")
            # 멀티셀렉트로 복수 선택 가능 (예: 점심, 저녁)
            f_eat_times = st.multiselect("먹는 시간", TIME_SLOTS, default=["점심"])
            submitted = st.form_submit_button("등록하기")

            if submitted:
                if not f_name.strip():
                    st.error("영양제 이름을 입력해주세요.")
                else:
                    eat_time_str = ", ".join(f_eat_times) if f_eat_times else "점심"
                    new_item = {
                        "id": str(uuid.uuid4()),
                        "name": f_name.strip(),
                        "dosage": f_dosage.strip(),
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
                    st.success(f"'{f_name}'이(가) 목록에 추가되었습니다.")
                    st.rerun()

    st.divider()
    st.subheader("복용 중인 영양제")

    if not st.session_state.supplements:
        st.info("아직 등록된 영양제가 없습니다. 위에서 영양제를 추가해보세요.")
    else:
        for item in st.session_state.supplements:
            with st.container(border=True):
                header_col, delete_col = st.columns([6, 1])
                with header_col:
                    st.markdown(
                        f"**{item['name']}** · {item['dosage'] or '섭취량 미입력'} "
                        f"&nbsp;<span style='color:#0284c7;font-weight:bold;'>[{item.get('eat_time', '점심')}]</span> "
                        f"&nbsp;<span style='color:#888;font-size:0.8rem'>({item['start_date']} 시작)</span>",
                        unsafe_allow_html=True
                    )
                with delete_col:
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
