import streamlit as st
import google.generativeai as genai

# 페이지 설정
st.set_page_config(
    page_title="복용 기록부",
    page_icon="💊",
    layout="centered"
)

# Gemini API 설정 (Streamlit Secrets에서 키 가져오기)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 안정적인 텍스트 생성 모델 지정
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception:
    model = None

# 메인 타이틀 및 설명
st.title("복용 기록부")
st.write("처방약과 영양제를 한 곳에서 정리하고 확인하세요.")

st.warning(
    "이 정보는 AI가 조회한 참고용 자료이며 부정확하거나 최신이 아닐 수 있습니다. "
    "실제 복용 여부와 병용 가능 여부는 반드시 약사 또는 의사와 상담한 뒤 결정하세요."
)

tab1, tab2 = st.tabs(["처방약", "영양제"])

with tab1:
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        drug_input = st.text_input(
            "약 이름 입력", 
            placeholder="예: 타이레놀 또는 오메가3", 
            label_visibility="collapsed"
        )
    with col2:
        ai_search = st.button("Q AI로 조회", use_container_width=True)
    with col3:
        direct_input = st.button("+ 직접 입력", use_container_width=True)

    # 'Q AI로 조회' 버튼을 눌렀을 때
    if ai_search:
        if not drug_input.strip():
            st.error("검색할 약 또는 영양제 이름을 입력해주세요.")
        elif not model:
            st.error("Gemini API 키가 설정되지 않았거나 올바르지 않습니다. Streamlit Secrets를 확인해주세요.")
        else:
            with st.spinner(f"'{drug_input}'에 대한 정보를 Gemini AI가 검색 중입니다..."):
                try:
                    # 프롬프트 구성
                    prompt = f"""
                    당신은 전문 약사입니다. 다음 약 또는 영양제에 대해 알려주세요: {drug_input}
                    효능/효과, 권장 복용 방법, 주의사항을 포함하여 간결하고 명확하게 마크다운 형식으로 정리해 주세요.
                    """
                    
                    # Gemini 모델 호출
                    response = model.generate_content(prompt)
                    ai_result = response.text
                    
                    st.success(f"'{drug_input}'에 대한 AI 검색 결과입니다.")
                    
                    # AI가 생성한 실제 내용을 Expander에 표시
                    with st.expander(f"💊 {drug_input} 상세 정보 확인하기", expanded=True):
                        st.markdown(ai_result)
                        
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

with tab2:
    st.info("영양제 관리 탭입니다.")
