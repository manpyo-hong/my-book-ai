import streamlit as st
from google import genai
from datetime import date
import uuid
import gspread
from google.oauth2.service_account import Credentials

# 페이지 설정
st.set_page_config(
    page_title="복용 기록부",
    page_icon="💊",
    layout="centered"
)

# 최신 Gemini 클라이언트 초기화 (Streamlit Secrets에서 키 가져오기)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
except Exception:
    client = None

# 카드 간격을 줄이기 위한 커스텀 CSS
st.markdown("""
<style>
[data-testid="stVerticalBlockBorderWrapper"] {
    padding: 0.6rem 1rem !important;
}
div.element-container {
    margin-bottom: 0.1rem !important;
}
[data-testid="stCheckbox"] {
    margin-top: -0.3rem;
    margin-bottom: -0.6rem;
}
</style>
""", unsafe_allow_html=True)

TIME_SLOTS = ["아침", "점심", "저녁", "취침 전"]
SHEET_HEADER = ["id", "name", "dosage", "start_date", "times", "taken_date"] + TIME_SLOTS


# ---------------- 구글 시트 연동 ----------------
@st.cache_resource
def get_worksheet():
    """서비스 계정으로 인증하고 영양제 시트를 반환. 시트가 없으면 새로 만듦."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["GOOGLE_SHEET_ID"])
    try:
        ws = sh.worksheet("supplements")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="supplements", rows=200, cols=len(SHEET_HEADER))
        ws.append_row(SHEET_HEADER)
    return ws


def sheets_enabled() -> bool:
    return "GOOGLE_SHEET_ID" in st.secrets and "gcp_service_account" in st.secrets


def load_supplements_from_sheet():
    """시트의 모든 행을 읽어서 앱에서 쓰는 형태로 변환. 오늘 날짜가 아니면 체크 상태는 초기화된 것으로 취급."""
    ws = get_worksheet()
    records = ws.get_all_records()
    today = date.today().isoformat()
    supplements = []
    for r in records:
        if not r.get("id"):
            continue
        times = [t for t in str(r.get("times", "")).split(",") if t]
        taken_date = str(r.get("taken_date", ""))
        taken = {}
        for t in TIME_SLOTS:
            raw = r.get(t, "")
            taken[t] = (taken_date == today) and str(raw).upper() == "TRUE"
        supplements.append({
            "id": r["id"],
            "name": r.get("name", ""),
            "dosage": r.get("dosage", ""),
            "start_date": r.get("start_date", ""),
            "times": times if times else ["아침"],
            "taken": taken,
        })
    return supplements


def append_supplement_to_sheet(item):
    ws = get_worksheet()
    row = [
        item["id"], item["name"], item["dosage"], item["start_date"],
        ",".join(item["times"]), "",
    ] + ["" for _ in TIME_SLOTS]
    ws.append_row(row)


def delete_supplement_from_sheet(item_id):
    ws = get_worksheet()
    cell = ws.find(item_id)
    if cell:
        ws.delete_rows(cell.row)


def update_taken_in_sheet(item_id, taken_dict):
    ws = get_worksheet()
    cell = ws.find(item_id)
    if not cell:
        return
    header = ws.row_values(1)
    today = date.today().isoformat()
    ws.update_cell(cell.row, header.index("taken_date") + 1, today)
    for t in TIME_SLOTS:
        col = header.index(t) + 1
        ws.update_cell(cell.row, col, "TRUE" if taken_dict.get(t) else "FALSE")


def ai_lookup(name: str) -> str:
    """Gemini에게 약/영양제 정보를 물어보고 마크다운 텍스트를 반환"""
    prompt = f"""
    당신은 전문 약사입니다. 다음 약 또는 영양제에 대해 알려주세요: {name}
    효능/효과, 권장 복용 방법, 주의사항을 포함하여 간결하고 명확하게 마크다운 형식으로 정리해 주세요.
    """
    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=prompt,
    )
    return response.text


# 세션 상태 초기화: 앱이 처음 로드될 때 한 번만 시트에서 불러옴
if "supplements" not in st.session_state:
    if sheets_enabled():
        try:
            st.session_state.supplements = load_supplements_from_sheet()
            st.session_state.sheet_error = None
        except Exception as e:
            st.session_state.supplements = []
            st.session_state.sheet_error = str(e)
    else:
        st.session_state.supplements = []
        st.session_state.sheet_error = "not_configured"


# 메인 타이틀 및 설명
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
        drug_input = st.text_input(
            "약 이름 입력",
            placeholder="예: 타이레놀 또는 오메가3",
            label_visibility="collapsed",
            key="drug_name_input"
        )
    with col2:
        ai_search = st.button("Q AI로 조회", use_container_width=True, key="drug_ai_search")
    with col3:
        direct_input = st.button("+ 직접 입력", use_container_width=True, key="drug_direct_input")

    if ai_search:
        if not drug_input.strip():
            st.error("검색할 약 또는 영양제 이름을 입력해주세요.")
        elif not client:
            st.error("Gemini API 키가 설정되지 않았거나 올바르지 않습니다. Streamlit Secrets를 확인해주세요.")
        else:
            with st.spinner(f"'{drug_input}'에 대한 정보를 Gemini AI가 검색 중입니다..."):
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
        st.info(
            "구글 시트 연동이 설정되지 않아 지금은 이 브라우저 세션에만 임시로 저장됩니다. "
            "Secrets에 GOOGLE_SHEET_ID와 gcp_service_account를 추가하면 영구 저장됩니다."
        )
    elif st.session_state.get("sheet_error"):
        st.error(f"구글 시트 연결에 실패했습니다: {st.session_state['sheet_error']}")

    st.subheader("영양제 등록")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        supp_input = st.text_input(
            "영양제 이름 입력",
            placeholder="예: 오메가3 프리미엄",
            label_visibility="collapsed",
            key="supp_name_input"
        )
    with col2:
        supp_ai_search = st.button("Q AI로 조회", use_container_width=True, key="supp_ai_search")
    with col3:
        supp_direct_input = st.button("+ 직접 입력", use_container_width=True, key="supp_direct_input")

    # AI 조회 결과를 세션에 보관 (등록 버튼을 눌러도 결과가 사라지지 않도록)
    if supp_ai_search:
        if not supp_input.strip():
            st.error("검색할 영양제 이름을 입력해주세요.")
        elif not client:
            st.error("Gemini API 키가 설정되지 않았거나 올바르지 않습니다. Streamlit Secrets를 확인해주세요.")
        else:
            with st.spinner(f"'{supp_input}'에 대한 정보를 Gemini AI가 검색 중입니다..."):
                try:
                    st.session_state["supp_ai_result"] = ai_lookup(supp_input)
                    st.session_state["supp_ai_result_name"] = supp_input
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

    if st.session_state.get("supp_ai_result"):
        with st.expander(f"💊 {st.session_state['supp_ai_result_name']} 상세 정보 확인하기", expanded=True):
            st.markdown(st.session_state["supp_ai_result"])

    # 직접 입력 또는 AI 조회 후 등록 폼 표시
    show_form = supp_direct_input or bool(st.session_state.get("supp_ai_result"))

    if show_form:
        with st.form("add_supplement_form", clear_on_submit=True):
            st.write("복용 중인 목록에 추가하기")
            f_name = st.text_input("영양제 이름", value=supp_input if supp_input else "")
            f_dosage = st.text_input("1회 섭취량 (예: 1정, 2캡슐)", value="")
            f_times = st.multiselect("섭취 시간대", TIME_SLOTS, default=["아침"])
            submitted = st.form_submit_button("등록하기")

            if submitted:
                if not f_name.strip():
                    st.error("영양제 이름을 입력해주세요.")
                else:
                    new_item = {
                        "id": str(uuid.uuid4()),
                        "name": f_name.strip(),
                        "dosage": f_dosage.strip(),
                        "start_date": date.today().isoformat(),
                        "times": f_times if f_times else ["아침"],
                        "taken": {t: False for t in TIME_SLOTS},
                    }
                    if sheets_enabled():
                        try:
                            append_supplement_to_sheet(new_item)
                        except Exception as e:
                            st.error(f"구글 시트 저장에 실패했습니다: {e}")
                    st.session_state.supplements.append(new_item)
                    st.session_state.pop("supp_ai_result", None)
                    st.session_state.pop("supp_ai_result_name", None)
                    st.success(f"'{f_name}'이(가) 목록에 추가되었습니다.")
                    st.rerun()

    st.divider()
    st.subheader("복용 중인 영양제")

    if not st.session_state.supplements:
        st.info("아직 등록된 영양제가 없습니다. 위에서 AI 조회 또는 직접 입력으로 추가해보세요.")
    else:
        for item in st.session_state.supplements:
            with st.container(border=True):
                header_col, delete_col = st.columns([6, 1])
                with header_col:
                    st.markdown(
                        f"**{item['name']}** · {item['dosage'] or '섭취량 미입력'} "
                        f"&nbsp;<span style='color:#888;font-size:0.8rem'>"
                        f"{item['start_date']} · {', '.join(item['times'])}</span>",
                        unsafe_allow_html=True
                    )
                with delete_col:
                    if st.button("삭제", key=f"delete_{item['id']}", use_container_width=True):
                        if sheets_enabled():
                            try:
                                delete_supplement_from_sheet(item["id"])
                            except Exception as e:
                                st.error(f"구글 시트에서 삭제하지 못했습니다: {e}")
                        st.session_state.supplements = [
                            s for s in st.session_state.supplements if s["id"] != item["id"]
                        ]
                        st.rerun()

                check_cols = st.columns(len(item["times"]) if item["times"] else 1)
                for i, t in enumerate(item["times"]):
                    with check_cols[i]:
                        prev_value = item["taken"].get(t, False)
                        checked = st.checkbox(
                            t,
                            value=prev_value,
                            key=f"check_{item['id']}_{t}"
                        )
                        if checked != prev_value:
                            item["taken"][t] = checked
                            if sheets_enabled():
                                try:
                                    update_taken_in_sheet(item["id"], item["taken"])
                                except Exception as e:
                                    st.error(f"구글 시트 업데이트에 실패했습니다: {e}")

        taken_count = sum(
            1 for s in st.session_state.supplements for t in s["times"] if s["taken"].get(t)
        )
        total_count = sum(len(s["times"]) for s in st.session_state.supplements)
        if total_count > 0:
            st.progress(taken_count / total_count, text=f"오늘 섭취 {taken_count}/{total_count} 완료")
