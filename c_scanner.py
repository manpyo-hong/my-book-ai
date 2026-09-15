import streamlit as st
from google import genai
from google.genai import types
from pptx import Presentation
from pptx.util import Pt
from io import BytesIO
import json
import re

# ---------------------------------------------------------
# 페이지 설정
# ---------------------------------------------------------
st.set_page_config(page_title="C언어 코드 & 실행결과 분석기", page_icon="💻")

st.title("💻 C언어 책 사진 ➔ 코드 해설 & PPT 변환기")
st.write(
    "C언어 예제 책 페이지를 여러 장 찍어 올리면, AI가 코드 분석과 실행 결과 풀이를 "
    "담은 여러 슬라이드의 학습 PPT를 만들어 드립니다!"
)

# ---------------------------------------------------------
# API 키 입력
# ---------------------------------------------------------
api_key = st.text_input("Gemini API 키를 입력하세요", type="password")

# ---------------------------------------------------------
# 파일 업로드 (여러 장 지원)
# ---------------------------------------------------------
uploaded_files = st.file_uploader(
    "C언어 책 페이지 사진을 업로드하거나 촬영하세요 (여러 장 선택 가능)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

if uploaded_files:
    cols = st.columns(min(len(uploaded_files), 4))
    for i, f in enumerate(uploaded_files):
        with cols[i % len(cols)]:
            st.image(f, caption=f"페이지 {i + 1}", use_container_width=True)


# ---------------------------------------------------------
# Gemini에게 "구조화된 JSON"으로 응답하도록 요청
# -> 슬라이드를 여러 장으로 나눠 만들기 위함
# ---------------------------------------------------------
def analyze_c_code_pages(client: genai.Client, images: list[bytes], mime_types: list[str]) -> dict:
    prompt = (
        "당신은 C언어 책의 예제 코드를 학습 슬라이드로 정리해주는 도우미입니다. "
        "첨부된 C언어 책 페이지 사진들을 분석해서 학습 노트를 만들어주세요.\n\n"
        "다음 JSON 형식으로만 응답하세요. 다른 설명, 마크다운 코드블록(```) "
        "표시는 절대 포함하지 마세요:\n\n"
        "{\n"
        '  "title": "전체 학습 노트 제목 (예: OO 예제 코드 분석 노트)",\n'
        '  "sections": [\n'
        "    {\n"
        '      "heading": "슬라이드 제목",\n'
        '      "bullets": ["요점 1", "요점 2", "요점 3"]\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "섹션은 반드시 다음 3가지로 구성하세요:\n"
        "1. 코드 핵심 목적 및 문법 설명\n"
        "2. 주요 함수 및 연산자 풀이\n"
        "3. 예상 실행 결과 및 화면 설명\n\n"
        "각 섹션의 bullets는 2~5개, 한 줄에 너무 길지 않게 간결한 문장으로 작성하세요. "
        "특수문자(**, ###, - 등)는 쓰지 마세요. 변수명이나 함수명은 그대로 써도 됩니다."
    )

    parts = [
        types.Part.from_bytes(data=img, mime_type=mt)
        for img, mt in zip(images, mime_types)
    ]
    parts.append(prompt)

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=parts,
    )

    raw_text = (response.text or "").strip()
    if not raw_text:
        raise ValueError(
            "AI가 빈 응답을 반환했습니다. 안전 필터에 걸렸거나 이미지를 "
            "인식하지 못했을 수 있습니다. 다른 사진으로 다시 시도해보세요."
        )

    # 혹시 모델이 ```json ... ``` 코드블록으로 감싸서 보낼 경우 제거
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # JSON 파싱 실패 시, 최소한 하나의 슬라이드로라도 보여주기 위한 대비책
        data = {
            "title": "C언어 학습 및 코드 분석 노트",
            "sections": [{"heading": "분석 결과", "bullets": [raw_text]}],
        }

    return data


# ---------------------------------------------------------
# 텍스트 프레임에 자동 줄맞춤 + 글자 수에 따른 폰트 크기 조절
# ---------------------------------------------------------
def set_autofit_text(text_frame, bullets: list[str]):
    text_frame.word_wrap = True
    total_chars = sum(len(b) for b in bullets)

    if total_chars > 500:
        font_size = Pt(14)
    elif total_chars > 250:
        font_size = Pt(16)
    else:
        font_size = Pt(18)

    text_frame.clear()
    for i, bullet in enumerate(bullets):
        p = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
        p.text = bullet
        p.level = 0
        p.font.size = font_size


# ---------------------------------------------------------
# python-pptx로 여러 슬라이드 PPT 생성 (메모리에서 바로 생성)
# ---------------------------------------------------------
def build_pptx(data: dict) -> BytesIO:
    prs = Presentation()

    # 1. 표지 슬라이드
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    slide.shapes.title.text = data.get("title", "C언어 학습 및 코드 분석 노트")
    for p in slide.shapes.title.text_frame.paragraphs:
        p.font.size = Pt(32)
        p.font.bold = True
    if len(slide.placeholders) > 1:
        slide.placeholders[1].text = "AI가 자동으로 생성한 C언어 학습 노트"

    # 2. 섹션별 내용 슬라이드
    content_layout = prs.slide_layouts[1]
    for section in data.get("sections", []):
        slide = prs.slides.add_slide(content_layout)
        slide.shapes.title.text = section.get("heading", "내용")
        for p in slide.shapes.title.text_frame.paragraphs:
            p.font.size = Pt(24)
            p.font.bold = True

        body = slide.placeholders[1]
        bullets = section.get("bullets", []) or ["내용 없음"]
        set_autofit_text(body.text_frame, bullets)

    buf = BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------
# 메인 로직
# ---------------------------------------------------------
if uploaded_files and api_key:
    if st.button("C언어 코드 분석 및 PPT 변환 시작"):
        with st.spinner("AI가 C언어 코드를 해설하고 실행 결과를 분석하는 중입니다..."):
            try:
                client = genai.Client(api_key=api_key)

                images = [f.getvalue() for f in uploaded_files]
                mime_types = [f.type for f in uploaded_files]

                data = analyze_c_code_pages(client, images, mime_types)
                pptx_buffer = build_pptx(data)

                st.success("C언어 분석 및 PPT 생성 완료!")

                st.download_button(
                    label="📥 C언어 학습 PPT 파일 다운로드",
                    data=pptx_buffer,
                    file_name="c_study_note.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )

                st.markdown("---")
                st.markdown(f"### 📝 {data.get('title', 'C언어 코드 해설 및 실행 결과 풀이')}")
                for section in data.get("sections", []):
                    st.markdown(f"**{section.get('heading', '')}**")
                    for b in section.get("bullets", []):
                        st.markdown(f"- {b}")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

elif uploaded_files and not api_key:
    st.warning("위쪽 빈칸에 Gemini API 키를 먼저 입력해 주세요!")
elif api_key and not uploaded_files:
    st.info("C언어 책 페이지 사진을 한 장 이상 업로드해주세요.")
