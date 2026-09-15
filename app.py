from google import genai
from google.genai import types
import streamlit as st
import os
from pptx import Presentation
from pptx.util import Inches, Pt

# 페이지 설정
st.set_page_config(page_title="책 사진 PPT 변환기", page_icon="📚")

st.title("📚 책 사진 ➔ 파워포인트(PPT) 변환기")
st.write("책 페이지를 사진으로 찍어 올리면, 깔끔한 공부용 PPT 파일로 정리해서 만들어 드립니다!")

# API 키 입력
api_key = st.text_input("Gemini API 키를 입력하세요", type="password")

# 파일 업로드 (스마트폰 카메라 연동)
uploaded_file = st.file_uploader("책 사진을 업로드하거나 촬영하세요", type=["jpg", "jpeg", "png"])

if uploaded_file is not None and api_key:
    st.image(uploaded_file, caption="업로드된 책 사진", use_container_width=True)
    
    if st.button("PPT 학습 자료로 변환 시작"):
        with st.spinner("AI가 책을 분석하고 PPT를 만드는 중입니다..."):
            try:
                # 1. Gemini AI 호출 (텍스트를 깔끔하게 정리해달라고 요청)
                client = genai.Client(api_key=api_key)
                image_bytes = uploaded_file.getvalue()
                
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=uploaded_file.type,
                        ),
                        "이 책 페이지 사진을 분석해서 3가지 항목으로 나누어줘. "
                        "1번 항목은 '1. 핵심 주제 및 개요', 2번 항목은 '2. 주요 내용 및 개념', 3번 항목은 '3. 핵심 요약 및 시사점'으로 하고, "
                        "특수문자(**, ### 등)는 쓰지 말고 깔끔한 일반 텍스트 문장 형태로만 작성해줘.",
                    ],
                )
                
                raw_text = response.text
                
                # 2. python-pptx를 이용해 파워포인트 파일 생성
                prs = Presentation()
                slide_layout = prs.slide_layouts[1] # 제목과 내용이 있는 레이아웃
                slide = prs.slides.add_slide(slide_layout)
                
                title_shape = slide.shapes.title
                title_shape.text = "AI 학습 요약 노트"
                
                body_shape = slide.placeholders[1]
                tf = body_shape.text_frame
                tf.text = raw_text # AI가 정리한 텍스트를 PPT 본문에 쏙 넣기
                
                # 임시 파일로 저장
                ppt_path = "study_note.pptx"
                prs.save(ppt_path)
                
                st.success("PPT 파일 생성 완료!")
                
                # 3. 다운로드 버튼 제공
                with open(ppt_path, "rb") as file:
                    st.download_button(
                        label="📥 요약된 PPT 파일 다운로드",
                        data=file,
                        file_name="book_study_note.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                    
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
elif uploaded_file is not None and not api_key:
    st.warning("위쪽 빈칸에 Gemini API 키를 먼저 입력해 주세요!")
