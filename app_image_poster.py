import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="Hao Harbour 官方海报旗舰版", layout="wide")

def load_font(size):
    font_path = "simhei.ttf"
    if os.path.exists(font_path):
        try: return ImageFont.truetype(font_path, size)
        except: return ImageFont.truetype(font_path, size, index=0)
    return ImageFont.load_default()

def call_ai_summary(desc):
    API_KEY = "sk-d99a91f22bf340139a335fb3d50d0ef5"
    API_URL = "https://api.deepseek.com/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    prompt = f"你是一个房产专家。请根据描述写一个精简的海报文案。要求：1.标题吸睛。2.每一行信息必须以 '-' 开头。3.纯中文，不要特殊符号。\n\n原文：{desc}"
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 新功能：手动画一个“勾”，永不乱码 ---
def draw_checkmark(draw, x, y, size=30, color=(30, 30, 30)):
    # 比例点：勾的起点、转折点、终点
    points = [(x, y + size//2), (x + size//3, y + size), (x + size, y)]
    draw.line(points, fill=color, width=5)

# --- 水印升级：更深、更大、不截断 ---
def add_custom_watermark(image, text):
    txt_layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
    # 字体加大到 180
    font = load_font(180)
    # 颜色加深 (透明度 120)
    color = (80, 80, 80, 120) 
    
    # 渲染文字
    temp_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    txt_img = Image.new('RGBA', (tw + 100, th + 100), (255, 255, 255, 0))
    d = ImageDraw.Draw(txt_img)
    d.text((50, 50), text, font=font, fill=color)
    
    # 旋转 30 度（更平缓，不容易被边缘切断）
    rotated = txt_img.rotate(30, expand=True, resample=Image.BICUBIC)
    rw, rh = rotated.size
    
    # 放置两个水印：一个偏左上，一个偏右下
    w, h = image.size
    image.paste(rotated, (w//10, h//4), rotated) # 左移：w//6 变成 w//10
    image.paste(rotated, (w//2 - 100, h//2 + 200), rotated)
    
    return image

def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    rows = (len(images) + 1) // 2
    
    # 画布初始化
    poster = Image.new('RGB', (canvas_w, 5000), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 图片排版
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

    # --- 文案与画勾逻辑 ---
    clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s,，.。\-\/]', '', text)
    font = load_font(46)
    cur_y = rows * (img_h + gap) + 80
    
    for line in clean_text.split('\n'):
        line = line.strip()
        if not line: continue
        
        # 如果这一行是列表项
        is_list = line.startswith('-')
        content = line.lstrip('- ').strip()
        
        wrapped = textwrap.wrap(content, width=22 if is_list else 24)
        for idx, wl in enumerate(wrapped):
            if is_list and idx == 0:
                draw_checkmark(draw, 80, cur_y + 10) # 在第一行画勾
                draw.text((130, cur_y), wl, fill=(30, 30, 30), font=font)
            else:
                indent = 130 if is_list else 80
                draw.text((indent, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 85
        cur_y += 10

    # 精准裁剪
    final_poster = poster.crop((0, 0, canvas_w, cur_y + 80))
    # 转 RGBA 加水印
    final_poster = add_custom_watermark(final_poster.convert('RGBA'), "Hao Harbour")
    
    buf = io.BytesIO()
    final_poster.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 Hao Harbour 海报旗舰版 (水印&勾号完美修复)")
desc = st.text_area("粘贴 Description")
files = st.file_uploader("上传房源照片", accept_multiple_files=True)

if st.button("🚀 生成最终版海报"):
    if desc and files:
        with st.spinner("正在绘制完美勾号与加深水印..."):
            poster_data = create_poster(files[:6], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("📥 下载海报图片", poster_data, "hao_harbour_final.png")
