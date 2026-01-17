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

def draw_checkmark(draw, x, y, size=30, color=(30, 30, 30)):
    points = [(x, y + size//2), (x + size//3, y + size), (x + size, y)]
    draw.line(points, fill=color, width=5)

# --- 水印升级：居中、旋转、不截断 ---
def add_centered_watermark(image, text):
    # 转为 RGBA 方便处理透明度
    img = image.convert('RGBA')
    width, height = img.size
    
    # 创建一个和原图一样大的透明层
    txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
    # 字体大小 180
    font = load_font(180)
    # 颜色加深，透明度 120
    fill = (70, 70, 70, 120) 

    # 为了旋转文字且不被截断，我们先在一个小图上画字
    # 计算文字宽高
    temp_draw = ImageDraw.Draw(txt_layer)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    # 创建文字小图，预留旋转空间
    txt_img = Image.new('RGBA', (tw + 200, th + 200), (255, 255, 255, 0))
    d = ImageDraw.Draw(txt_img)
    d.text((100, 100), text, font=font, fill=fill)
    
    # 旋转 20 度（角度越小越不容易出界）
    rotated_txt = txt_img.rotate(20, expand=True, resample=Image.BICUBIC)
    rw, rh = rotated_txt.size

    # 计算两个居中位置
    # 位置1：上半部分（图片区域）中心
    pos1 = (width // 2 - rw // 2, height // 4 - rh // 2)
    # 位置2：下半部分（文字区域）中心
    pos2 = (width // 2 - rw // 2, height * 3 // 4 - rh // 2)

    # 粘贴水印到透明层
    txt_layer.paste(rotated_txt, pos1, rotated_txt)
    txt_layer.paste(rotated_txt, pos2, rotated_txt)

    # 合并原图和水印层
    return Image.alpha_composite(img, txt_layer)

def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    rows = (len(images) + 1) // 2
    
    # 初始化超长画布
    poster = Image.new('RGB', (canvas_w, 5000), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 拼图
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

    # 文案排版
    clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s,，.。\-\/]', '', text)
    font = load_font(46)
    cur_y = rows * (img_h + gap) + 80
    
    for line in clean_text.split('\n'):
        line = line.strip()
        if not line: continue
        
        is_list = line.startswith('-')
        content = line.lstrip('- ').strip()
        
        wrapped = textwrap.wrap(content, width=22 if is_list else 24)
        for idx, wl in enumerate(wrapped):
            if is_list and idx == 0:
                draw_checkmark(draw, 80, cur_y + 10)
                draw.text((130, cur_y), wl, fill=(30, 30, 30), font=font)
            else:
                indent = 130 if is_list else 80
                draw.text((indent, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 85
        cur_y += 10

    # 精确裁剪底部
    final_poster = poster.crop((0, 0, canvas_w, cur_y + 80))
    
    # 添加两个居中的大水印
    watermarked_poster = add_centered_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked_poster.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 Hao Harbour 海报")
desc = st.text_area("粘贴 Description")
files = st.file_uploader("上传图片", accept_multiple_files=True)

if st.button("🚀 生成海报"):
    if desc and files:
        with st.spinner("正在生成海报..."):
            poster_data = create_poster(files[:6], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("📥 下载海报图片", poster_data, "hao_harbour_poster.png")
