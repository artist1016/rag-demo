import streamlit as st
import requests
import tempfile
import math
import re
from pypdf import PdfReader
from docx import Document
import os

# ---------- 页面配置 ----------
st.set_page_config(page_title="智能问答助手", page_icon="💬", layout="wide")

# ---------- 自定义紫色样式 ----------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e9eff5 100%);
    }
    h1 {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem !important;
    }
    .stButton > button {
        background-color: #3b82f6;
        color: white;
        border-radius: 0.375rem;
        border: none;
        padding: 0.5rem 0.75rem;
        font-weight: 500;
        font-size: 0.9rem;
        transition: all 0.2s;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #2563eb;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .stTextInput > div > div > input {
        border-radius: 0.5rem;
        border: 1px solid #d1d5db;
        padding: 0.75rem 1rem;
        font-size: 1rem;
    }
    .stTextInput > div > div > input:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 2px rgba(99,102,241,0.2);
    }
    .row-widget.stHorizontal {
        gap: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------- 侧边栏：个人信息 ----------
with st.sidebar:
    st.image("https://pic3.zhimg.com/v2-9d6e739cc0100488e3de6abb1518d46a_1440w.jpg", width=120)  # 可选头像
    st.markdown("## 代")
    st.markdown("**全栈开发 · AI 应用开发者**")
    st.markdown("---")
    
    st.markdown("### 🛠️ 核心技术")
    st.markdown("""
    - Python / FastAPI / Flask
    - TypeScript / React / Next.js
    - Neo4j / MySQL
    - LangChain / RAG / 大模型 API
    """)
    
    st.markdown("### 📌 近期项目")
    st.markdown("""
    - **应急知识图谱问答系统** (毕设，已开源)
    - **交互式数据可视化网站** (Next.js + Plotly)
    - **RAG 文档问答助手** (本应用，智谱 GLM)
    """)
    
    st.markdown("### 📫 联系")
    st.markdown("""
    - GitHub: [github.com/yourname](https://github.com/artist1016)
    - Email: 1137251662@qq.com@example.com
    """)
    
    st.markdown("---")
    st.caption("© 2026 Dai | RAG Demo Powered by Zhipu AI")


# ---------- 读取 API Key ----------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 优先从环境变量读取（包括 .env 和 Streamlit Cloud 的 secrets 注入）
ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY')

# 如果没有，尝试从 st.secrets 读取（兼容旧方式）
if not ZHIPU_API_KEY:
    try:
        ZHIPU_API_KEY = st.secrets.get('ZHIPU_API_KEY')
    except Exception:
        pass

if not ZHIPU_API_KEY:
    st.error("未找到 ZHIPU_API_KEY，请在 .env 文件或 Streamlit secrets 中配置")
    st.stop()

ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZHIPU_EMBEDDING_URL = "https://open.bigmodel.cn/api/paas/v4/embeddings"

# ---------- 调用 LLM ----------
def ask_llm(prompt, system_prompt=None):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    headers = {"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "glm-4-flash", "messages": messages, "temperature": 0}
    response = requests.post(ZHIPU_API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"❌ 调用失败: {response.text}"

# ---------- 初始化 session_state ----------
if 'uploaded_doc_text' not in st.session_state:
    st.session_state.uploaded_doc_text = None
if 'doc_name' not in st.session_state:
    st.session_state.doc_name = None

# ---------- 主界面 ----------
st.title("💬 智能问答助手")
st.markdown("直接在下方输入问题，点击「搜索」获得回答；或点击「上传文档」后基于文档内容回答。")

# 输入框和按钮布局 - 输入框占更大比例，按钮适当变小
col_input, col_btn1, col_btn2 = st.columns([6, 1, 1])
with col_input:
    question = st.text_input("", placeholder="输入你的问题...", label_visibility="collapsed", key="question_input")
with col_btn1:
    search_clicked = st.button("🔍 搜索", use_container_width=True)
with col_btn2:
    upload_clicked = st.button("📄 上传文档", use_container_width=True)

# 处理上传文档按钮
if upload_clicked:
    uploaded_file = st.file_uploader("选择 PDF 或 Word 文档", type=["pdf", "docx"], key="doc_uploader")
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name
        full_text = ""
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(tmp_path)
            for page in reader.pages:
                full_text += page.extract_text()
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(tmp_path)
            full_text = "\n".join([p.text for p in doc.paragraphs])
        else:
            st.error("不支持的文件类型")
            st.stop()
        if full_text.strip():
            st.session_state.uploaded_doc_text = full_text
            st.session_state.doc_name = uploaded_file.name
            st.success(f"已上传文档：{uploaded_file.name}，共 {len(full_text)} 字符")
        else:
            st.error("文档内容为空")
    else:
        st.info("请选择一个文档")

# 显示已上传文档信息
if st.session_state.uploaded_doc_text:
    st.info(f"📄 当前已加载文档：{st.session_state.doc_name}，可直接提问")

# 处理搜索按钮
if search_clicked and question:
    if st.session_state.uploaded_doc_text:
        doc_text = st.session_state.uploaded_doc_text
        if len(doc_text) > 20000:
            doc_text = doc_text[:20000]
            st.warning("文档较长，仅使用前 20000 字符")
        with st.spinner("AI 正在阅读文档并思考..."):
            prompt = f"请根据以下文档内容回答问题：\n\n{doc_text}\n\n问题：{question}\n\n回答："
            answer = ask_llm(prompt)
    else:
        with st.spinner("AI 思考中..."):
            answer = ask_llm(question)
    st.markdown("### 🤖 回答")
    st.write(answer)
elif search_clicked and not question:
    st.warning("请输入问题")