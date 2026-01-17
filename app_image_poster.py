import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="Hao Harbour 官方海报生成器", layout="wide")

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
    prompt = f"你是一个房产专家。请根据描述写一个极其精简的海报文案。要求：1.标题吸睛。2.每一行信息必须以 '-' 开头。3.直接输出纯文本，严禁使用任何 ** 或 # 符号。\n\n原文：{desc}"
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 3. 倾斜水印逻辑 ---
def add_diagonal_watermark(image, text):
    # 创建水印层
    watermark = Image.new('RGBA', image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(watermark)
    font = load_font(120)
    
    # 设置水印颜色和透明度 (灰度 120, 透明度 100)
    color = (120, 120, 120, 100)
    
    # 计算倾斜角度并在临时小图上绘制，然后旋转
    # 为简化代码并保证性能，我们在多个位置绘制，达到覆盖效果
    w, h = image.size
    for x in range(0, w, 400):
        for y in range(0, h, 400):
            # 绘制背景水印
            draw.text((x, y), text, font=font, fill=color)

    # 合并
    return Image.alpha_composite(image.convert('RGBA'), watermark)

# --- 4. 海报合成 ---
def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    rows = (len(images) + 1) // 2
    
    # 初始给一个足够大的画布，后面会裁剪
    poster = Image.new('RGB', (canvas_w, 5000), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 放置图片 (1行2张)
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

    # --- 文案排版 ---
    clean_text = re.sub(r'[*#_~`>]', '', text)
    # 强制将所有连字符替换为最稳的“√”
    clean_text = clean_text.replace("-", "√") 
    
    font = load_font(44)
    cur_y = rows * (img_h + gap) + 80
    
    for line in clean_text.split('\n'):
        line = line.strip()
        if not line: continue
        # 自动换行
        wrapped = textwrap.wrap(line, width=24)
        for wl in wrapped:
            draw.text((80, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 75
        cur_y += 15

    # 版权小字
    draw.text((80, cur_y + 40), "Hao Harbour Real Estate", fill=(150, 150, 150), font=load_font(30))
    
    # --- 智能裁剪：切掉多余底部 ---
    final_h = cur_y + 150
    poster = poster.crop((0, 0, canvas_w, final_h))
    
    # --- 添加水印 ---
    poster_with_wm = add_diagonal_watermark(poster, "Hao Harbour")
    
    buf = io.BytesIO()
    poster_with_wm.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- Streamlit UI ---
st.title("🏡 Hao Harbour 房产海报终极版")
desc = st.text_area("1. 粘贴 Description")
files = st.file_uploader("2. 上传照片 (1-6张)", accept_multiple_files=True)

if st.button("🚀 生成带倾斜水印海报"):
    if desc and files:
        with st.spinner("正在生成并精确裁剪..."):
            poster_data = create_poster(files[:6], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("📥 下载海报", poster_data, "hao_harbour.png")
