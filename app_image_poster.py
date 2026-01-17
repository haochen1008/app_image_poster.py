import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="Hao Harbour 官方海报", layout="wide")

def load_font(size):
    font_path = "simhei.ttf"
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except:
            return ImageFont.truetype(font_path, size, index=0)
    return ImageFont.load_default()

def call_ai_summary(desc):
    API_KEY = "sk-d99a91f22bf340139a335fb3d50d0ef5"
    API_URL = "https://api.deepseek.com/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    # 强制 AI 只输出最简单的文字，不要任何 markdown 符号
    prompt = f"你是一个房产专家。请根据描述写一个精简的海报文案。要求：1.标题吸睛。2.每一行信息必须以 '-' 开头。3.纯文本，严禁使用任何 ** 或 # 或特殊 Emoji 符号。\n\n原文：{desc}"
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 核心改进：45度大水印，仅2个 ---
def add_custom_watermark(image, text):
    # 创建透明层
    watermark_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(watermark_layer)
    # 字体加大
    font = load_font(150)
    color = (150, 150, 150, 90) # 灰色，透明度 90
    
    # 创建一个临时的文字图片用来旋转
    text_w, text_h = draw.textbbox((0, 0), text, font=font)[2:]
    txt_img = Image.new('RGBA', (text_w, text_h), (255, 255, 255, 0))
    d = ImageDraw.Draw(txt_img)
    d.text((0, 0), text, font=font, fill=color)
    
    # 旋转 45 度
    rotated_txt = txt_img.rotate(45, expand=1)
    
    # 放置两个水印：一个偏上，一个偏下
    w, h = image.size
    image.paste(rotated_txt, (w//6, h//4), rotated_txt)
    image.paste(rotated_txt, (w//2, h//2), rotated_txt)
    
    return image

def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    rows = (len(images) + 1) // 2
    
    # 动态预估高度
    poster = Image.new('RGB', (canvas_w, 5000), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
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

    # --- 文案逻辑：极简安全模式 ---
    # 过滤所有特殊符号
    clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s,，.。\-\/]', '', text)
    # 强制将连杠换成字母 v，这是最稳的“勾号”替代品
    clean_text = clean_text.replace("-", "v ") 
    
    font = load_font(46)
    cur_y = rows * (img_h + gap) + 80
    
    for line in clean_text.split('\n'):
        line = line.strip()
        if not line: continue
        wrapped = textwrap.wrap(line, width=24)
        for wl in wrapped:
            draw.text((80, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 80
        cur_y += 10

    # 裁剪：精准切断底部，不留黑边
    final_poster = poster.crop((0, 0, canvas_w, cur_y + 100))
    
    # 添加品牌水印
    final_poster = add_custom_watermark(final_poster.convert('RGBA'), "Hao Harbour")
    
    buf = io.BytesIO()
    final_poster.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# UI 部分
st.title("🏡 Hao Harbour 房产海报 (无乱码倾斜水印版)")
desc = st.text_area("粘贴 Description")
files = st.file_uploader("上传图片", accept_multiple_files=True)

if st.button("生成海报"):
    if desc and files:
        with st.spinner("处理中..."):
            poster_data = create_poster(files[:6], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("下载图片", poster_data, "poster.png")
