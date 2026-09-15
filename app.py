from google import genai
from google.genai import types
import streamlit as st
import os
from pptx import Presentation
from pptx.util import Pt

# 페이지 설정
st.set_page_config(page_title="책 사진 PPT 변환기", page_icon="📚")

st.title("📚 책 사진 ➔ 내용 요약 및 파워포인트(PPT) 변환기")
st.write("책 페이지를 사진으로 찍어 올리면, 화면에서 요약을 확인하고 상단에서 세련된 PPT 파일을 바로 다운로드할 수 있습니다!")

# API 키 입력
api_key = st.text_input("Gemini API 키를 입력하세요", type="password")

# 파일 업로드 (스마트폰 카메라 연동)
uploaded_file = st.file_uploader("책 사진을 업로드하거나 촬영하세요", type=["jpg", "jpeg", "png"])

if uploaded_file is not None and api_key:
    st.image(uploaded_file, caption="업로드된 책 사진", use_container_width=True)
    
    if st.button("AI 분석 및 PPT 변환 시작"):
        with st.spinner("AI가 책을 분석하고 PPT를 만드는 중입니다..."):
            try:
                # 1. Gemini AI 호출
                client = genai.Client(api_key=api_key)
                image_bytes = uploaded_file.getvalue()
                
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=uploaded_file.type,
                        ),
                        "이 책 페이지 사진을 분석해서 1. 핵심 주제 및 개요, 2. 주요 내용 및 개념, 3. 핵심 요약 및 시사점 형태로 정리해줘. "
                        "특수문자(**, ### 등)는 쓰지 말고 깔끔한 일반 텍스트 문장 형태로만 작성해줘.",
                    ],
                )
                
                raw_text = response.text
                
                # 2. python-pptx를 이용해 파워포인트 파일 미리 생성
                prs = Presentation()
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                
                # 제목 스타일 지정
                title_shape = slide.shapes.title
                title_shape.text = "AI 학습 요약 노트"
                for paragraph in title_shape.text_frame.paragraphs:
                    paragraph.font.size = Pt(22)
                    paragraph.font.bold = True
                
                # 본문 스타일 지정 (글자를 작고 세련되게 조절)
                body_shape = slide.placeholders[1]
                tf = body_shape.text_frame
                tf.text = raw_text
                
                for paragraph in tf.paragraphs:
                    paragraph.font.size = Pt(13)
                
                # 임시 파일로 저장
                ppt_path = "study_note.pptx"
                prs.save(ppt_path)
                
                st.success("분석 완료!")
                
                # 3. 💡 PPT 다운로드 버튼을 상단(요약 결과 표시 전)에 배치
                with open(ppt_path, "rb") as file:
                    st.download_button(
                        label="📥 [상단] 세련된 요약 PPT 파일 다운로드",
                        data=file,
                        file_name="book_study_note.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                
                st.markdown("---")
                
                # 4. 하단에 AI 요약 내용 표시
                st.markdown("### 📝 AI 요약 결과")
                st.markdown(raw_text)
                    
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
elif uploaded_file is not None and not api_key:
    st.warning("위쪽 빈칸에 Gemini API 키를 먼저 입력해 주세요!")
