from google import genai
from google.genai import types
import streamlit as st
import os
from pptx import Presentation
from pptx.util import Inches, Pt

# 페이지 설정
st.set_page_config(page_title="책 사진 PPT 자동 요약기", page_icon="📚")

st.title("📚 책 사진 ➔ 파워포인트(PPT) 학습 요약기")
st.write("책 페이지를 사진으로 찍어 올리면, AI가 요약해서 PPT 파일로 만들어 드립니다!")

# API 키 입력 받기 (또는 코드 내에 고정 입력 가능)
api_key = st.text_input("Gemini API 키를 입력하세요", type="password")

# 파일 업로드 (스마트폰에서 카메라 촬영 연동 가능)
uploaded_file = st.file_uploader("책 사진을 업로드하거나 촬영하세요", type=["jpg", "jpeg", "png"])

def create_ppt(summary_text):
    """요약된 텍스트를 바탕으로 PPT 파일을 생성하는 함수"""
    prs = Presentation()
    
    # 빈 슬라이드 레이아웃 추가 (제목 + 내용 레이아웃)
    slide_layout = prs.slide_layouts[1] 
    slide = prs.slides.add_slide(slide_layout)
    
    # 제목 설정
    title = slide.shapes.title
    title.text = "AI 학습 요약 노트"
    
    # 본문 내용 설정
    body = slide.placeholders[1]
    body.text = summary_text
    
    # 서버 임시 폴더에 파일 저장
    file_path = "study_summary.pptx"
    prs.save(file_path)
    return file_path

if uploaded_file is not None and api_key:
    st.image(uploaded_file, caption="업로드된 책 사진", use_container_width=True)
    
    if st.button("AI 요약 및 PPT 생성 시작"):
        with st.spinner("AI가 책을 분석하고 PPT를 제작하는 중입니다..."):
            try:
                # 클라이언트 초기화
                client = genai.Client(api_key=api_key)
                image_bytes = uploaded_file.getvalue()
                
                # Gemini API 호출 (최신 모델 반영)
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=uploaded_file.type,
                        ),
                        "이 책 페이지 사진을 분석해서 공부하기 좋게 핵심 주제, 주요 개념 및 설명을 글머리 기호 위주로 깔끔하고 간결하게 요약해줘.",
                    ],
                )
                
                summary_result = response.text
                
                st.success("분석 및 PPT 생성 완료!")
                st.markdown("### 📝 AI 요약 미리보기")
                st.markdown(summary_result)
                
                # PPT 파일 생성 실행
                ppt_file = create_ppt(summary_result)
                
                # 다운로드 버튼 제공
                with open(ppt_file, "rb") as f:
                    st.download_button(
                        label="📥 요약된 파워포인트(PPT) 파일 다운로드",
                        data=f,
                        file_name="book_study_summary.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
elif uploaded_file is not None and not api_key:
    st.warning("위쪽 빈칸에 Gemini API 키를 먼저 입력해 주세요!")
