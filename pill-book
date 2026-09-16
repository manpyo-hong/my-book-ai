import streamlit as st

# 페이지 설정 (브라우저 탭 제목 및 아이콘)
st.set_page_config(
    page_title="복용 기록부",
    page_icon="💊",
    layout="centered"
)

# 1. 메인 타이틀 및 설명
st.title("복용 기록부")
st.write("처방약과 영양제를 한 곳에서 정리하고 확인하세요.")

# 2. 경고 박스 (st.warning 활용)
st.warning(
    "이 정보는 AI가 웹 검색으로 조회한 참고용 자료이며 부정확하거나 최신이 아닐 수 있습니다. "
    "실제 복용 여부와 병용 가능 여부는 반드시 약사 또는 의사와 상담한 뒤 결정하세요."
)

# 3. 탭 메뉴 (처방약 / 영양제)
tab1, tab2 = st.tabs(["처방약", "영양제"])

with tab1:
    # 4. 입력창과 버튼을 나란히 배치 (Columns 활용)
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        # label_visibility="collapsed"를 주어 라벨 글자를 숨기고 깔끔한 입력창만 남김
        drug_input = st.text_input(
            "약 이름 입력", 
            placeholder="예: 타이레놀", 
            label_visibility="collapsed"
        )
    with col2:
        ai_search = st.button("Q AI로 조회", use_container_width=True)
    with col3:
        direct_input = st.button("+ 직접 입력", use_container_width=True)

    # 5. 'Q AI로 조회' 버튼을 눌렀을 때 동작하는 예시 로직
    if ai_search:
        if drug_input.strip() == "":
            st.error("검색할 약 이름을 입력해주세요.")
        else:
            st.success(f"'{drug_input}'에 대한 AI 검색 결과입니다.")
            
            # 조회 결과 리스트 (Expander 활용)
            with st.expander(f"💊 {drug_input}정 500mg (예시 정보 확인하기)", expanded=True):
                st.markdown("### 📋 상세 정보")
                st.write("- **효능/효과:** 해열, 진통, 감기로 인한 발열 및 통증 완화")
                st.write("- **복용 방법:** 성인 기준 1회 1~2정, 4~6시간 간격 복용 (1일 최대 4,000mg 초과 금지)")
                st.write("- **주의사항:** 음주 후 복용 시 간 손상이 유발될 수 있습니다.")

with tab2:
    st.info("영양제 관리 탭입니다. 복용 중인 영양제를 추가하고 기록해 보세요.")
    # 영양제 입력 영역 추후 확장 가능
    supplement_input = st.text_input("영양제 이름 입력", placeholder="예: 비타민 C")
    if st.button("영양제 추가"):
        if supplement_input:
            st.success(f"'{supplement_input}' 영양제가 등록되었습니다!")
