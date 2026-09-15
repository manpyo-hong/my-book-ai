from google import genai
from google.genai import types
import streamlit as st
import os
from pptx import Presentation
from pptx.util import Pt

# 페이지 설정
st.set_page_config(page_title="C언어 코드 & 실행결과 분석기", page_icon="💻")

st.title("💻 C언어 책 사진 ➔ 코드 해설 & PPT 변환기")
st.write("C언어 예제 책 페이지를 찍어 올리면, AI가 코드 분석과 실행 결과 풀이를 담은 세련된 학습 PPT를 만들어 드립니다!")

# API 키 입력
api_key = st.text_input("Gemini API 키를 입력하세요", type="password")

# 파일 업로드 (스마트폰 카메라 연동)
uploaded_file = st.file_uploader("C언어 책 페이지 사진을 업로드하거나 촬영하세요", type=["jpg", "jpeg", "png"])

if uploaded_file is not None and api_key:
    st.image(uploaded_file, caption="업로드된 C언어 책 사진", use_container_width=True)
    
    if st.button("C언어 코드 분석 및 PPT 변환 시작"):
        with st.spinner("AI가 C언어 코드를 해설하고 실행 결과를 분석하는 중입니다..."):
            try:
                # 1. Gemini AI 호출 (C언어 맞춤형 프롬프트)
                client = genai.Client(api_key=api_key)
                image_bytes = uploaded_file.getvalue()
                
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=uploaded_file.type,
                        ),
                        "이 C언어 책 페이지 사진을 분석해서 다음 3가지 항목으로 나누어 정돈된 텍스트로 작성해줘. "
                        "1. 코드 핵심 목적 및 문법 설명, "
                        "2. 주요 함수 및 연산자 풀이, "
                        "3. 예상 실행 결과 및 화면 설명. "
                        "특수문자(**, ### 등)는 쓰지 말고 깔끔한 일반 텍스트 문장 형태로만 작성해줘.",
                    ],
                )
                
                raw_text = response.text
                
                # 2. python-pptx를 이용해 C언어 학습용 PPT 생성
                prs = Presentation()
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                
                # 제목 스타일 지정
                title_shape = slide.shapes.title
                title_shape.text = "💻 C언어 학습 및 코드 분석 노트"
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
                ppt_path = "c_study_note.pptx"
                prs.save(ppt_path)
                
                st.success("C언어 분석 및 PPT 생성 완료!")
                
                # 3. PPT 다운로드 버튼을 최상단에 배치
                with open(ppt_path, "rb") as file:
                    st.download_button(
                        label="📥 [상단] C언어 학습 PPT 파일 다운로드",
                        data=file,
                        file_name="c_study_note.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                
                st.markdown("---")
                
                # 4. 하단에 AI 분석 내용 표시
                st.markdown("### 📝 C언어 코드 해설 및 실행 결과 풀이")
                st.markdown(raw_text)
                    
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
elif uploaded_file is not None and not api_key:
    st.warning("위쪽 빈칸에 Gemini API 키를 먼저 입력해 주세요!")
