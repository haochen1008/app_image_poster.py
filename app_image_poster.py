import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="Hao Harbour 房产海报生成器", layout="wide")

# --- 1. 字体加载 ---
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
    prompt = f"你是一个房产专家。请根据描述写一个精简的海报文案。要求：1.标题吸睛。2.列表式列出核心信息（位置、房型、租金、入住时间）。3.全部中文，多用Emoji。严禁使用 ** 或 # 符号。\n\n原文：{desc}"
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 3. 核心：添加水印的函数 ---
def add_watermark(base_image, text):
    # 创建一个和原图一样大的透明图层
    txt_layer = Image.new('RGBA', base_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)
    font = load_font(80) # 水印字体大一些
    
    # 颜色设置为浅灰色 + 半透明
    fill_color = (150, 150, 150, 40) 
    
    # 在图片中心位置绘制倾斜水印
    # 这里的循环是为了在图片上下多放几个水印，防止别人裁剪
    width, height = base_image.size
    for i in range(1, 4):
        pos = (width // 4, height * i // 4)
        draw.text(pos, text, font=font, fill=fill_color)

    # 合并图层
    return Image.alpha_composite(base_image.convert('RGBA'), txt_layer)

# --- 4. 海报合成 ---
def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    rows = (len(images) + 1) // 2
    poster_h = rows * (img_h + gap) + 1200
    
    poster = Image.new('RGB', (canvas_w, poster_h), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 拼图排版
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

    # 文案逻辑
    text = re.sub(r'[#*`_~]', '', text)
    text = text.replace("- ", "√ ")
    text = text.replace("位置:", "📍 位置:").replace("租金:", "💰 租金:")
    
    font = load_font(42)
    cur_y = rows * (img_h + gap) + 80
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        for wl in textwrap.wrap(line, width=26):
            draw.text((80, cur_y), wl, fill=(40, 40, 40), font=font)
            cur_y += 75
        cur_y += 10

    # 绘制右下角固定品牌印记
    brand_font = load_font(30)
    draw.text((canvas_w - 300, cur_y + 50), "© Hao Harbour Real Estate", fill=(180, 180, 180), font=brand_font)

    final_poster = poster.crop((0, 0, canvas_w, cur_y + 120))
    
    # --- 调用水印功能 ---
    watermarked_poster = add_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked_poster.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 Hao Harbour 专属海报生成 (带水印防伪)")
desc_in = st.text_area("1. 粘贴 Description")
files_in = st.file_uploader("2. 上传照片 (1-6张)", accept_multiple_files=True)

if st.button("🎨 生成海报"):
    if desc_in and files_in:
        with st.spinner("AI 正在工作并添加水印..."):
            poster_data = create_poster(files_in[:6], call_ai_summary(desc_in))
            st.image(poster_data)
            st.download_button("📥 下载带水印海报", poster_data, "hao_harbour_poster.png")
