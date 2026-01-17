import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="Hao Harbour 专业海报生成器", layout="wide")

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
    # 强制 AI 输出标准格式
    prompt = f"你是一个房产专家。请根据描述写一个精简的海报文案。要求：1.标题吸睛。2.每一行信息必须以 '-' 开头。3.全部中文，多用Emoji。严禁使用 ** 或 # 符号。\n\n原文：{desc}"
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 3. 水印逻辑 (加深版) ---
def add_watermark(base_image, text):
    # 创建图层
    txt_layer = Image.new('RGBA', base_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)
    font = load_font(100) # 水印字体加大
    
    # 【修改重点】颜色改为深灰色 (100,100,100)，透明度调高到 80 (之前是40)
    fill_color = (100, 100, 100, 80) 
    
    width, height = base_image.size
    # 在图片上平铺 6 个水印，确保无法被裁剪
    positions = [
        (width//6, height//4), (width//2, height//4),
        (width//6, height//2), (width//2, height//2),
        (width//6, height*3//4), (width//2, height*3//4)
    ]
    
    for pos in positions:
        # 稍微倾斜水印 (通过新建小图旋转实现太复杂，这里直接平铺)
        draw.text(pos, text, font=font, fill=fill_color)

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
    
    # 1行2张图片排列
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

    # --- 【修改重点】解决勾号乱码 ---
    # 去除 Markdown
    text = re.sub(r'[*#_~`>]', '', text)
    # 弃用特殊字符勾号，改用标准的中文符号“√”或者直接画一个
    text = text.replace("- ", "√ ") 
    
    font = load_font(44)
    cur_y = rows * (img_h + gap) + 80
    
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        
        wrapped = textwrap.wrap(line, width=24)
        for wl in wrapped:
            draw.text((80, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 75
        cur_y += 15

    # 底部版权声明
    draw.text((canvas_w - 450, cur_y + 50), "Hao Harbour Real Estate", fill=(100, 100, 100), font=load_font(35))

    final_poster = poster.crop((0, 0, canvas_w, cur_y + 150))
    # 添加加深版水印
    watermarked = add_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 Hao Harbour 房产海报生成器")
desc = st.text_area("粘贴描述")
files = st.file_uploader("照片 (最多6张)", accept_multiple_files=True)

if st.button("生成海报"):
    if desc and files:
        with st.spinner("正在合成带水印的海报..."):
            summary = call_ai_summary(desc)
            poster_data = create_poster(files[:6], summary)
            st.image(poster_data)
            st.download_button("下载海报", poster_data, "hao_harbour.png")
