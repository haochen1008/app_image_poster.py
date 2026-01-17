import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="专业房源海报-勾号排版版", layout="wide")

# --- 1. 字体加载 (确保使用你上传的 simhei.ttf) ---
def load_font(size):
    font_path = "simhei.ttf"
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except:
            return ImageFont.truetype(font_path, size, index=0)
    return ImageFont.load_default()

# --- 2. AI 文案生成 ---
def call_ai_summary(desc):
    API_KEY = "sk-d99a91f22bf340139a335fb3d50d0ef5"
    API_URL = "https://api.deepseek.com/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    # 强制 AI 使用列表格式，不要带任何特殊 Markdown 符号
    prompt = f"""
    你是一个房产专家。请根据描述写一个精简的海报文案。
    要求：
    1. 标题必须有吸引力。
    2. 核心信息（位置、房型、租金、入住时间）必须分行，且每行以 '-' 开头。
    3. 亮点部分也请以 '-' 开头。
    4. 纯文本，不要 ** 或 # 符号。
    原文：{desc}
    """
    
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 3. 海报合成 (勾号转换逻辑) ---
def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    rows = (len(images) + 1) // 2
    poster_h = rows * (img_h + gap) + 1200
    
    poster = Image.new('RGB', (canvas_w, poster_h), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 拼图排版 (1行2张)
    for i, img_file in enumerate(images):
        img = Image.open(img_file).convert("RGB")
        tw = (canvas_w - gap * 3) // 2
        scale = max(tw/img.width, img_h/img.height)
        img = img.resize((int(img.width*scale), int(img.height*scale)), Image.Resampling.LANCZOS)
        left, top = (img.width-tw)/2, (img.height-img_h)/2
        img = img.crop((left, top, left+tw, top+img_h))
        x = gap if i % 2 == 0 else tw + gap * 2
        y = (i // 2) * (img_h + gap) + gap
        poster.paste(img, (x, y))

    # --- 关键修改：符号清洗与勾号替换 ---
    # 去除 Markdown 干扰
    text = re.sub(r'[#*`_~]', '', text)
    # 将 AI 生成的横杠 '-' 替换为中文语境下兼容性最好的勾号 '√'
    text = text.replace("- ", "√ ")
    text = text.replace("位置:", "📍 位置:")
    text = text.replace("房型:", "🏠 房型:")
    text = text.replace("租金:", "💰 租金:")
    text = text.replace("入住:", "📅 入住:")
    text = text.replace("亮点:", "✨ 亮点:")

    font = load_font(42)
    cur_y = rows * (img_h + gap) + 80
    margin = 80
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            cur_y += 30
            continue
        
        # 自动换行
        wrapped_lines = textwrap.wrap(line, width=26)
        for wl in wrapped_lines:
            # 绘制文字，填充颜色选深灰色更显高级
            draw.text((margin, cur_y), wl, fill=(35, 35, 35), font=font)
            cur_y += 75
        cur_y += 10

    # 裁剪底部多余白边
    return poster.crop((0, 0, canvas_w, cur_y + 100))

# --- UI 界面 ---
st.title("🏡 房产海报生成器 (专业勾号排版)")
st.markdown("---")

desc_in = st.text_area("1. 粘贴 Rightmove Description", height=200)
files_in = st.file_uploader("2. 上传房源照片 (最多6张)", accept_multiple_files=True)

if st.button("🎨 立即合成海报"):
    if desc_in and files_in:
        with st.spinner("AI 正在优化文案并添加专业勾号..."):
            summary = call_ai_summary(desc_in)
            poster_img = create_poster(files_in[:6], summary)
            st.image(poster_img)
            
            # 转为字节流下载
            buf = io.BytesIO()
            poster_img.save(buf, format='PNG')
            st.download_button("📥 点击下载高清海报图片", buf.getvalue(), "house_poster.png", "image/png")
    else:
        st.warning("提示：请确认已粘贴文字并上传至少一张图片。")
