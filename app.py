from google import genai
from google.genai import types
import streamlit as st

st.set_page_config(page_title="책 사진 공부 요약기", page_icon="📚")

st.title("📚 책 사진 ➔ AI 스터디 요약기")
st.write("책 페이지를 사진으로 찍거나 업로드하면, AI가 핵심 내용을 요약해 드립니다!")

# API 키 입력칸 (안전하게 비밀번호 형태로 입력)
api_key = st.text_input("Gemini API 키를 입력하세요", type="password")

# 스마트폰 카메라 촬영 또는 파일 업로드
uploaded_file = st.file_uploader("책 사진을 업로드하거나 촬영하세요", type=["jpg", "jpeg", "png"])

if uploaded_file is not None and api_key:
    st.image(uploaded_file, caption="업로드된 책 사진", use_container_width=True)
    
    if st.button("AI 분석 및 요약 시작"):
        with st.spinner("AI가 열심히 책을 읽고 분석하는 중입니다..."):
            try:
                client = genai.Client(api_key=api_key)
                image_bytes = uploaded_file.getvalue()
                
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=uploaded_file.type,
                        ),
                        "이 책 페이지 사진을 분석해서 1. 핵심 주제, 2. 주요 개념 및 설명(글머리 기호), 3. 핵심 요약 정리를 보기 쉽게 마크다운 형식으로 작성해줘.",
                    ],
                )
                
                st.success("분석 완료!")
                st.markdown("### 📝 AI 요약 결과")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
elif uploaded_file is not None and not api_key:
    st.warning("위쪽 빈칸에 Gemini API 키를 먼저 입력해 주세요!")
