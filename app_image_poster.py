import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="Hao Harbour 旗舰版-日期保障", layout="wide")

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
    
    # --- 提示词优化：明确包含入住时间，剔除杂项 ---
    prompt = (
        "你是一个房产专家。请根据描述写一个精简的海报文案。要求：\n"
        "1. 标题吸睛。\n"
        "2. 核心信息必须包含：位置、房型、租金、入住时间（起租日期）。\n"
        "3. 每一行信息以 '-' 开头。\n"
        "4. 严禁输出'长租类型'和'最短租期'，这些不重要。\n"
        "5. 纯中文，租金保留英镑符号 £。\n\n"
        f"原文：{desc}"
    )
    
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

def draw_checkmark(draw, x, y, size=30, color=(30, 30, 30)):
    points = [(x, y + size//2), (x + size//3, y + size), (x + size, y)]
    draw.line(points, fill=color, width=5)

def add_centered_watermark(image, text):
    img = image.convert('RGBA')
    width, height = img.size
    txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
    
    font = load_font(200) # 字体大一度
    fill = (50, 50, 50, 120) # 颜色深两度

    temp_draw = ImageDraw.Draw(txt_layer)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    txt_img = Image.new('RGBA', (tw + 200, th + 200), (255, 255, 255, 0))
    d = ImageDraw.Draw(txt_img)
    d.text((100, 100), text, font=font, fill=fill)
    
    rotated_txt = txt_img.rotate(20, expand=True, resample=Image.BICUBIC)
    rw, rh = rotated_txt.size

    # 两个大水印居中
    pos1 = (width // 2 - rw // 2, height // 4 - rh // 2)
    pos2 = (width // 2 - rw // 2, height * 3 // 4 - rh // 2)

    txt_layer.paste(rotated_txt, pos1, rotated_txt)
    txt_layer.paste(rotated_txt, pos2, rotated_txt)
    return Image.alpha_composite(img, txt_layer)

def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    rows = (len(images) + 1) // 2
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

    # 保留英镑符号 £
    clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s,，.。\-\/£]', '', text)
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

    # 智能裁剪并加水印
    final_poster = poster.crop((0, 0, canvas_w, cur_y + 80))
    watermarked = add_centered_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 Hao Harbour 海报旗舰版 (起租日期保障)")
