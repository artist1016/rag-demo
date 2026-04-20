import streamlit as st
import requests
import tempfile
import math
import re
from pypdf import PdfReader
from docx import Document
import os

# ---------- 页面配置 ----------
st.set_page_config(page_title="智能文档问答助手", page_icon="📚", layout="wide")

# ---------- 读取 API Key ----------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
    headers = {"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "embedding-2", "input": text}
    response = requests.post(ZHIPU_EMBEDDING_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["data"][0]["embedding"]
    else:
        st.error(f"Embedding API 错误: {response.text}")
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
    headers = {"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "glm-4-flash", "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    response = requests.post(ZHIPU_API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"❌ LLM 调用失败: {response.text}"

# ---------- 高亮关键词 ----------
def highlight_keywords(text, keywords):
    if not keywords:
        return text
    pattern = re.compile('|'.join(re.escape(kw) for kw in keywords), re.IGNORECASE)
    return pattern.sub(lambda m: f'<mark style="background-color: #fde047;">{m.group(0)}</mark>', text)

# ---------- Streamlit UI ----------
st.title("📚 智能文档问答助手")
st.markdown("上传 PDF 或 Word 文档，输入问题进行智能问答，也可在侧边栏搜索文档内容")

# 侧边栏：文档内搜索
with st.sidebar:
    st.header("🔍 文档内搜索")
    keyword_search = st.text_input("输入关键词（多个用逗号分隔）", placeholder="例如：人工智能, 算法")
    st.markdown("---")
    st.caption("💡 提示：搜索会在原始文档中高亮显示匹配内容")

# 主区域：文档上传 + 问答
uploaded = st.file_uploader("上传文档 (PDF/Word)", type=["pdf", "docx"])

if uploaded:
    # 提取文档文本
    with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded.name) as tmp:
        tmp.write(uploaded.getbuffer())
        tmp_path = tmp.name
    full_text = ""
    if uploaded.type == "application/pdf":
        reader = PdfReader(tmp_path)
        for page in reader.pages:
            full_text += page.extract_text()
    elif uploaded.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(tmp_path)
        full_text = "\n".join([p.text for p in doc.paragraphs])
    else:
        st.error("不支持的文件类型")
        st.stop()
    
    if not full_text.strip():
        st.error("未能提取文本")
        st.stop()
    
    st.info(f"文档已加载，共 {len(full_text)} 字符")
    
    # 文档内关键词搜索与高亮
    if keyword_search:
        keywords = [kw.strip() for kw in keyword_search.split(",") if kw.strip()]
        if keywords:
            highlighted = highlight_keywords(full_text, keywords)
            with st.expander(f"🔎 搜索 '{keyword_search}' 的结果", expanded=True):
                st.markdown(f'<div style="max-height: 300px; overflow-y: auto; border:1px solid #ddd; padding:10px; border-radius:10px; background-color:white;">{highlighted}</div>', unsafe_allow_html=True)
    
    # 文本分块
    chunks = split_text(full_text, chunk_size=500, overlap=50)
    
    # 缓存 embedding 结果（基于文档名）
    if 'chunk_embeddings' not in st.session_state or st.session_state.get('doc_id') != uploaded.name:
        with st.spinner("建立向量索引..."):
            chunk_embeddings = []
            progress_bar = st.progress(0)
            for i, chunk in enumerate(chunks):
                emb = get_embedding(chunk)
                if emb:
                    chunk_embeddings.append(emb)
                progress_bar.progress((i+1)/len(chunks))
            progress_bar.empty()
            st.session_state.chunk_embeddings = chunk_embeddings
            st.session_state.chunks = chunks
            st.session_state.doc_id = uploaded.name
        st.success("索引完成")
    else:
        chunk_embeddings = st.session_state.chunk_embeddings
        chunks = st.session_state.chunks
    
    # 问答输入框
    query = st.text_input("💬 输入问题", placeholder="例如：这篇文档的核心观点是什么？")
    
    if query:
        with st.spinner("检索中..."):
            q_emb = get_embedding(query)
            if q_emb is None:
                st.stop()
            similarities = [cosine_similarity(q_emb, ce) for ce in chunk_embeddings]
            best_idx = max(range(len(similarities)), key=lambda i: similarities[i])
            best_chunk = chunks[best_idx]
            score = similarities[best_idx]
        
        st.markdown(f"**最相关片段** (相似度 {score:.2%})")
        st.write(best_chunk)
        
        with st.spinner("生成回答..."):
            prompt = f"根据以下内容回答问题：\n\n{best_chunk}\n\n问题：{query}\n\n回答："
            answer = ask_llm(prompt)
        st.markdown("### 🤖 回答")
        st.write(answer)

else:
    st.info("请先上传 PDF 或 Word 文档")