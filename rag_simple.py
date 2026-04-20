from dotenv import load_dotenv
import os

load_dotenv()  # 加载 .env 文件中的变量

import streamlit as st
import requests
import json
import tempfile
import math
from pypdf import PdfReader
from docx import Document

# ---------- 页面配置 ----------
st.set_page_config(
    page_title="智能文档问答助手",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

with st.sidebar:
    st.image("https://pic3.zhimg.com/v2-9d6e739cc0100488e3de6abb1518d46a_r.jpg", width=120)  # 可选头像
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
    - Email: 1137251662@@qq.com
    """)
    
    st.markdown("---")
    st.caption("© 2026 Dai | RAG Demo Powered by Zhipu AI")

# ---------- 自定义 CSS 样式 ----------
st.markdown("""
<style>
    /* 主色调 */
    :root {
        --primary: #6366f1;
        --primary-dark: #4f46e5;
        --secondary: #10b981;
        --background: #f9fafb;
        --card-bg: #ffffff;
        --text: #1f2937;
        --text-light: #6b7280;
    }
    
    /* 全局字体 */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e9eff5 100%);
    }
    
    /* 主容器圆角卡片 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* 标题样式 */
    h1 {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem !important;
    }
    
    /* 副标题 */
    .subtitle {
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 2rem;
        border-left: 3px solid #6366f1;
        padding-left: 1rem;
    }
    
    /* 上传区域美化 */
    .stFileUploader > div {
        background-color: var(--card-bg);
        border: 2px dashed #cbd5e1;
        border-radius: 1rem;
        padding: 1.5rem;
        transition: all 0.3s ease;
    }
    .stFileUploader > div:hover {
        border-color: var(--primary);
        background-color: #f8fafc;
    }
    
    /* 卡片样式 */
    .info-card {
        background-color: var(--card-bg);
        border-radius: 1rem;
        padding: 1rem 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin: 1rem 0;
        border-left: 4px solid var(--primary);
    }
    
    .answer-card {
        background-color: #f0fdf4;
        border-radius: 1rem;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid var(--secondary);
    }
    
    /* 相似度标签 */
    .similarity-badge {
        background-color: #e0e7ff;
        color: #4338ca;
        border-radius: 9999px;
        padding: 0.2rem 0.8rem;
        font-size: 0.8rem;
        display: inline-block;
        margin-bottom: 0.5rem;
    }
    
    /* 引用片段 */
    .source-block {
        background-color: #fef9c3;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
        border-left: 3px solid #eab308;
    }
    
    /* 进度文本 */
    .progress-text {
        font-size: 0.85rem;
        color: #4b5563;
        margin-top: 0.5rem;
    }
    
    /* 按钮风格 */
    .stButton > button {
        background-color: var(--primary);
        color: white;
        border-radius: 0.5rem;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: var(--primary-dark);
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    
    /* 输入框 */
    .stTextInput > div > div > input {
        border-radius: 0.5rem;
        border: 1px solid #d1d5db;
        padding: 0.5rem 1rem;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 2px rgba(99,102,241,0.2);
    }
    
    /* 侧边栏定制 */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    [data-testid="stSidebar"] .sidebar-content {
        padding: 1.5rem;
    }
    .sidebar-header {
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 1rem;
        color: var(--primary);
    }
    hr {
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------- 智谱 API 配置 ----------
# 优先使用 st.secrets（Streamlit Cloud），其次使用环境变量
if hasattr(st, 'secrets') and 'ZHIPU_API_KEY' in st.secrets:
    ZHIPU_API_KEY = st.secrets['ZHIPU_API_KEY']
else:
    ZHIPU_API_KEY = os.getenv('ZHIPU_API_KEY')

if not ZHIPU_API_KEY:
    st.error("未找到 ZHIPU_API_KEY，请在 .env 文件或 Streamlit secrets 中配置")
    st.stop()
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZHIPU_EMBEDDING_URL = "https://open.bigmodel.cn/api/paas/v4/embeddings"

# ---------- 文本分块 ----------
def split_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i+chunk_size])
        chunks.append(chunk)
    return chunks

# ---------- 获取 embedding ----------
def get_embedding(text):
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "embedding-2",
        "input": text
    }
    response = requests.post(ZHIPU_EMBEDDING_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["data"][0]["embedding"]
    else:
        st.error(f"❌ Embedding API 错误: {response.text}")
        return None

# ---------- 余弦相似度 ----------
def cosine_similarity(a, b):
    dot_product = sum(x*y for x,y in zip(a,b))
    norm_a = math.sqrt(sum(x*x for x in a))
    norm_b = math.sqrt(sum(y*y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0
    return dot_product / (norm_a * norm_b)

# ---------- 调用 LLM ----------
def ask_llm(prompt):
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "glm-4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }
    response = requests.post(ZHIPU_API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"❌ LLM 调用失败: {response.text}"

# ---------- 侧边栏信息 ----------
with st.sidebar:
    st.markdown('<div class="sidebar-header">📖 使用说明</div>', unsafe_allow_html=True)
    st.markdown("""
    1. 上传 **PDF** 或 **Word** 文档  
    2. 等待系统自动建立索引  
    3. 输入问题，获得基于文档的智能回答  
    
    ---
    **✨ 技术亮点**
    - 智谱 GLM-4-Flash 免费模型
    - 语义检索 + 生成式问答
    - 支持中英文混合文档
    
    ---
    **⚡ 提示**
    首次处理稍慢，因为需调用 Embedding API。
    建议文档大小不超过 10MB。
    """)
    st.markdown("---")
    st.caption("Powered by Zhipu AI & Streamlit")

# ---------- 主界面 ----------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.title("📚 智能文档问答助手")
    st.markdown('<div class="subtitle">上传文档，让 AI 为你解读内容</div>', unsafe_allow_html=True)

# 文件上传区域
uploaded = st.file_uploader("", type=["pdf", "docx"], label_visibility="collapsed")

if uploaded:
    # 保存临时文件并提取文本
    with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded.name) as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = tmp.name

    full_text = ""
    file_type = uploaded.type
    if file_type == "application/pdf":
        reader = PdfReader(tmp_path)
        for page in reader.pages:
            full_text += page.extract_text()
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(tmp_path)
        full_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    else:
        st.error("不支持的文件类型")
        st.stop()

    if not full_text.strip():
        st.error("未能从文档中提取到文本内容")
        st.stop()

    # 显示文档基本信息
    with st.container():
        col_info1, col_info2, col_info3 = st.columns(3)
        col_info1.metric("📄 文档类型", "PDF" if file_type == "application/pdf" else "Word")
        col_info2.metric("📏 原始字符数", f"{len(full_text):,}")
        
    # 文本分块
    chunks = split_text(full_text, chunk_size=500, overlap=50)
    st.info(f"📑 文档已切分为 **{len(chunks)}** 个文本块（每块约500字）")

    # 计算 embedding 并显示进度条
    progress_bar = st.progress(0, text="正在建立向量索引...")
    status_text = st.empty()
    chunk_embeddings = []
    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk)
        if emb:
            chunk_embeddings.append(emb)
        progress = (i + 1) / len(chunks)
        progress_bar.progress(progress, text=f"处理中 {i+1}/{len(chunks)}")
        status_text.markdown(f'<div class="progress-text">⏳ 正在处理第 {i+1} 个文本块...</div>', unsafe_allow_html=True)
    
    progress_bar.empty()
    status_text.empty()

    if len(chunk_embeddings) != len(chunks):
        st.error("部分文本块 Embedding 失败，请检查网络或 API Key")
        st.stop()

    st.success(f"✅ 索引构建完成！已准备就绪，可以开始提问。")

    # 问答区域
    st.markdown("---")
    st.markdown("### 💬 提问")
    query = st.text_input("", placeholder="例如：这篇文档的核心观点是什么？", label_visibility="collapsed")
    
    if query:
        with st.spinner("🔍 正在检索最相关的段落..."):
            q_emb = get_embedding(query)
            if q_emb is None:
                st.stop()
            similarities = [cosine_similarity(q_emb, ce) for ce in chunk_embeddings]
            best_idx = max(range(len(similarities)), key=lambda i: similarities[i])
            best_chunk = chunks[best_idx]
            score = similarities[best_idx]

        # 显示检索结果
        st.markdown(f'<div class="similarity-badge">📌 相似度 {score:.2%}</div>', unsafe_allow_html=True)
        with st.expander("📖 查看引用的原文片段", expanded=False):
            st.markdown(f'<div class="source-block">{best_chunk}</div>', unsafe_allow_html=True)

        # 生成最终回答
        with st.spinner("🤖 正在生成回答..."):
            prompt = f"根据以下内容回答问题：\n\n{best_chunk}\n\n问题：{query}\n\n回答："
            answer = ask_llm(prompt)
        
        st.markdown('<div class="answer-card">', unsafe_allow_html=True)
        st.markdown("### ✨ 智能回答")
        st.write(answer)
        st.markdown('</div>', unsafe_allow_html=True)

        # 添加反馈提示
        st.caption("💡 提示：如果回答不准确，可以尝试换一种问法或上传更清晰的文档。")
else:
    # 未上传文件时的占位提示
    st.markdown("""
    <div style="text-align: center; padding: 3rem; background-color: #ffffff; border-radius: 1rem; margin-top: 2rem;">
        <span style="font-size: 3rem;">📂</span>
        <p style="color: #6b7280; margin-top: 1rem;">点击上方区域上传 PDF 或 Word 文档，开始智能问答</p>
    </div>
    """, unsafe_allow_html=True)