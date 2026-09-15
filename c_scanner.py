import streamlit as st
from google import genai
from google.genai import types
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from io import BytesIO
from st_img_pastebutton import paste
import base64
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

# ---------------------------------------------------------
# 클립보드에서 스크린샷 붙여넣기
# ---------------------------------------------------------
if "paste_count" not in st.session_state:
    st.session_state.paste_count = 0
if "pasted_images" not in st.session_state:
    st.session_state.pasted_images = []  # [(bytes, mime_type), ...]

st.markdown("**또는** 스크린샷을 캡처해 클립보드에 복사한 뒤, 아래 버튼을 클릭하세요")
st.caption(
    "💡 Ctrl+V가 아니라 **버튼 클릭**으로 동작합니다. "
    "Windows는 Win+Shift+S, Mac은 Cmd+Shift+4 누른 뒤 Control까지 같이 누르면 "
    "클립보드로 복사돼요. 복사 직후 바로 아래 버튼을 눌러주세요."
)
paste_col1, paste_col2 = st.columns([3, 1])

with paste_col1:
    pasted_data_url = paste(
        label="📋 클립보드 이미지 불러오기",
        key=f"paste_{st.session_state.paste_count}",
    )

with paste_col2:
    if pasted_data_url is not None:
        if st.button("➕ 이 이미지 추가"):
            header, encoded = pasted_data_url.split(",", 1)
            mime_type = header.split(";")[0].split(":")[1]
            binary_data = base64.b64decode(encoded)
            st.session_state.pasted_images.append((binary_data, mime_type))
            st.session_state.paste_count += 1  # 위젯을 새로 만들어 다음 붙여넣기를 받음
            st.rerun()

if st.session_state.pasted_images:
    if st.button("🗑️ 붙여넣은 이미지 전체 삭제"):
        st.session_state.pasted_images = []
        st.rerun()

# ---------------------------------------------------------
# 업로드 파일 + 붙여넣은 이미지 미리보기
# ---------------------------------------------------------
preview_items = []  # [(bytes, mime, caption), ...]
if uploaded_files:
    preview_items += [(f.getvalue(), f.type, f"업로드 {i + 1}") for i, f in enumerate(uploaded_files)]
preview_items += [
    (data, mime, f"붙여넣기 {i + 1}") for i, (data, mime) in enumerate(st.session_state.pasted_images)
]

if preview_items:
    cols = st.columns(min(len(preview_items), 4))
    for i, (data, _, caption) in enumerate(preview_items):
        with cols[i % len(cols)]:
            st.image(data, caption=caption, use_container_width=True)


# ---------------------------------------------------------
# Gemini에게 "구조화된 JSON"으로 응답하도록 요청
# -> 슬라이드를 여러 장으로 나눠 만들기 위함
# ---------------------------------------------------------
def analyze_c_code_pages(client: genai.Client, images: list[bytes], mime_types: list[str]) -> dict:
    prompt = (
        "당신은 C언어 책의 예제 코드를 학습 슬라이드로 정리해주는 도우미입니다. "
        "첨부된 C언어 책 페이지 사진들을 분석해서, 코딩 초보자가 영어 문장을 "
        "단어별로 해석하듯 코드를 한 줄씩 따라가며 이해할 수 있는 학습 노트를 만들어주세요.\n\n"
        "다음 JSON 형식으로만 응답하세요. 다른 설명, 마크다운 코드블록(```) "
        "표시는 절대 포함하지 마세요:\n\n"
        "{\n"
        '  "title": "전체 학습 노트 제목 (예: OO 예제 코드 분석 노트)",\n'
        '  "libraries": [\n'
        "    {\n"
        '      "name": "코드에 포함된 헤더/라이브러리 이름 (예: stdio.h)",\n'
        '      "description": "이 라이브러리가 왜 필요한지, 어떤 기능(입출력, 문자열 처리 등)을 "\n'
        '                      "제공하는지 한 문장으로 설명"\n'
        "    }\n"
        "  ],\n"
        '  "sections": [\n'
        "    {\n"
        '      "heading": "슬라이드 제목",\n'
        '      "bullets": ["요점 1", "요점 2", "요점 3"]\n'
        "    }\n"
        "  ],\n"
        '  "code_lines": [\n'
        "    {\n"
        '      "code": "사진 속 코드 원문 한 줄 또는 한 구문 (예: printf(\\"%d\\\\n\\", sum);)",\n'
        '      "explanation": "이 코드 한 줄이 정확히 무엇을 하는지 우리말로 해설"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "각 항목별 작성 규칙:\n"
        "- libraries: 코드 상단의 #include 등으로 쓰인 헤더를 모두 나열하세요. 없으면 빈 배열([])로 두세요.\n"
        "- sections: 반드시 다음 3가지로 구성하세요.\n"
        "  1. 코드 핵심 목적 및 문법 설명\n"
        "  2. 주요 함수 및 연산자 풀이\n"
        "  3. 예상 실행 결과 및 화면 설명\n"
        "  각 섹션의 bullets는 2~5개, 간결한 문장으로 작성하세요.\n"
        "- code_lines: 사진 속 코드에서 의미 있는 구문(변수 선언, 함수 호출, 조건문, 반복문, "
        "연산 등)을 코드에 나온 순서 그대로, 최대한 빠짐없이 나열하세요. 중괄호({ })만 있는 줄이나 "
        "빈 줄은 생략해도 되지만, 그 외에는 최대한 모든 실행 라인을 포함하세요 (보통 8~20줄). "
        "code 필드는 사진에 보이는 코드 그대로(들여쓰기, 세미콜론 포함) 적고, explanation은 "
        "그 줄이 프로그램에서 실제로 하는 동작을 초보자도 이해할 수 있게 풀어서 설명하세요.\n\n"
        "특수문자(**, ###, - 등 마크다운 기호)는 bullets와 explanation에 쓰지 마세요. "
        "변수명, 함수명, 코드 자체는 원문 그대로 써도 됩니다."
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
            "libraries": [],
            "sections": [{"heading": "분석 결과", "bullets": [raw_text]}],
            "code_lines": [],
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
# "라이브러리 설명" 슬라이드 추가
# ---------------------------------------------------------
def add_library_slide(prs, libraries: list[dict]):
    if not libraries:
        return
    layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(layout)
    slide.shapes.title.text = "사용된 라이브러리(헤더) 설명"
    for p in slide.shapes.title.text_frame.paragraphs:
        p.font.size = Pt(24)
        p.font.bold = True

    body = slide.placeholders[1]
    bullets = [
        f"{lib.get('name', '이름 없음')} : {lib.get('description', '')}"
        for lib in libraries
    ]
    set_autofit_text(body.text_frame, bullets)


# ---------------------------------------------------------
# "코드 한 줄씩 해설" 슬라이드 추가 (코드 → 설명 쌍을 함께 표시)
# ---------------------------------------------------------
def add_code_breakdown_slides(prs, code_lines: list[dict], lines_per_slide: int = 5):
    if not code_lines:
        return
    layout = prs.slide_layouts[1]

    for start in range(0, len(code_lines), lines_per_slide):
        chunk = code_lines[start:start + lines_per_slide]
        slide = prs.slides.add_slide(layout)
        end = start + len(chunk)
        slide.shapes.title.text = f"코드 한 줄씩 해설 ({start + 1}~{end}번째)"
        for p in slide.shapes.title.text_frame.paragraphs:
            p.font.size = Pt(22)
            p.font.bold = True

        tf = slide.placeholders[1].text_frame
        tf.word_wrap = True
        tf.clear()

        for i, item in enumerate(chunk):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()

            code_run = p.add_run()
            code_run.text = item.get("code", "")
            code_run.font.name = "Consolas"
            code_run.font.size = Pt(13)
            code_run.font.bold = True
            code_run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x99)

            arrow_run = p.add_run()
            arrow_run.text = "  →  "
            arrow_run.font.size = Pt(13)

            expl_run = p.add_run()
            expl_run.text = item.get("explanation", "")
            expl_run.font.size = Pt(13)


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

    # 2. 라이브러리 설명 슬라이드
    add_library_slide(prs, data.get("libraries", []))

    # 3. 섹션별 내용 슬라이드 (핵심 목적 / 함수 풀이 / 실행 결과)
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

    # 4. 코드 한 줄씩 해설 슬라이드 (코드 → 설명, 영어 직독직해처럼 매칭)
    add_code_breakdown_slides(prs, data.get("code_lines", []))

    buf = BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------
# 메인 로직
# ---------------------------------------------------------
if preview_items and api_key:
    if st.button("C언어 코드 분석 및 PPT 변환 시작"):
        with st.spinner("AI가 C언어 코드를 해설하고 실행 결과를 분석하는 중입니다..."):
            try:
                client = genai.Client(api_key=api_key)

                images = [item[0] for item in preview_items]
                mime_types = [item[1] for item in preview_items]

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

                libraries = data.get("libraries", [])
                if libraries:
                    st.markdown("#### 📚 사용된 라이브러리")
                    for lib in libraries:
                        st.markdown(f"- **{lib.get('name', '')}** : {lib.get('description', '')}")

                for section in data.get("sections", []):
                    st.markdown(f"**{section.get('heading', '')}**")
                    for b in section.get("bullets", []):
                        st.markdown(f"- {b}")

                code_lines = data.get("code_lines", [])
                if code_lines:
                    st.markdown("#### 🔍 코드 한 줄씩 해설")
                    for item in code_lines:
                        code_col, expl_col = st.columns([1, 1])
                        with code_col:
                            st.code(item.get("code", ""), language="c")
                        with expl_col:
                            st.markdown(item.get("explanation", ""))

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

elif preview_items and not api_key:
    st.warning("위쪽 빈칸에 Gemini API 키를 먼저 입력해 주세요!")
elif api_key and not preview_items:
    st.info("C언어 책 페이지 사진을 한 장 이상 업로드하거나 붙여넣어 주세요.")
