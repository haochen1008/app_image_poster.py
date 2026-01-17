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
    
    # 锁定图10的提取逻辑：结构化、详尽、无翻译
    prompt = (
        "你是一个房产文案专家。请严格按照以下结构提取房源信息，不要包含任何备注或说明：\n"
        "1. 标题：直接使用英文原名，如 'Lexington Gardens'。\n"
        "2. 地理位置：包含具体区域名（Nine Elms, London）和邮编，强调位于Vauxhall和Battersea Park之间。\n"
        "3. 房型配置：间数、卫浴数。\n"
        "4. 租金：月租XXXX磅，周租XXX磅（用逗号隔开）。\n"
        "5. 面积：平方英尺和平方米对照。\n"
        "6. 入住日期：具体日期。\n"
        "7. 公寓亮点：分‘设施’、‘交通’、‘周边’三个细项展示。\n"
        "要求：每行以 '√' 开头，保持专业简洁，严禁出现'最短租期'和'押金'。\n\n"
        f"原文：{desc}"
    )
    
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

def draw_checkmark(draw, x, y, size=32, color=(40, 40, 40)):
    points = [(x, y + size//2), (x + size//3, y + size), (x + size, y)]
    draw.line(points, fill=color, width=6)

def add_smart_watermark(image, text):
    img = image.convert('RGBA')
    w, h = img.size
    txt_layer = Image.new('RGBA', (w, h), (255, 255, 255, 0))
    font = load_font(220)
    fill = (40, 40, 40, 140) 
    temp_draw = ImageDraw.Draw(txt_layer)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    txt_img = Image.new('RGBA', (tw + 100, th + 100), (255, 255, 255, 0))
    ImageDraw.Draw(txt_img).text((50, 50), text, font=font, fill=fill)
    rotated = txt_img.rotate(18, expand=True, resample=Image.BICUBIC)
    rw, rh = rotated.size
    pos1 = (w//2 - rw//2, h//4 - rh//2)
    pos2 = (w//2 - rw//2, (h * 3)//4 - rh//2)
    txt_layer.paste(rotated, pos1, rotated)
    txt_layer.paste(rotated, pos2, rotated)
    return Image.alpha_composite(img, txt_layer)

def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    rows = (len(images) + 1) // 2
    poster = Image.new('RGB', (canvas_w, 8000), (255, 255, 255))
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

    # --- 改进的文本换行逻辑，防止截断 ---
    font = load_font(48)
    cur_y = rows * (img_h + gap) + 100
    margin = 80 # 左右边距
    max_txt_width = canvas_w - margin * 2 - 80 # 除去勾号占位的可用宽度
    
    # 过滤掉不需要的关键词
    bad_keywords = ["最短租期", "押金", "文案说明", "备注"]
    lines = [l for l in text.split('\n') if not any(k in l for k in bad_keywords)]

    for line in lines:
        line = line.strip()
        if not line: continue
        
        is_list = any(line.startswith(s) for s in ['-', 'v', '√', '*'])
        content = re.sub(r'^[-v√*]\s*', '', line)
        
        # 智能计算换行：保持单词完整的同时，绝不超出 1200px 宽度
        wrapped = textwrap.wrap(content, width=22, break_long_words=False)
        
        for idx, wl in enumerate(wrapped):
            current_x = 160 if is_list else 80
            if is_list and idx == 0:
                draw_checkmark(draw, 80, cur_y + 12)
            
            draw.text((current_x, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 90
        cur_y += 20

    final_poster = poster.crop((0, 0, canvas_w, cur_y + 120))
    watermarked = add_smart_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 Hao Harbour 官方海报")
desc = st.text_area("粘贴 Description")
files = st.file_uploader("上传图片", accept_multiple_files=True)

if st.button("🚀 生成海报"):
    if desc and files:
        with st.spinner("正在提取精华并优化排版..."):
            poster_data = create_poster(files[:6], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("📥 下载海报", poster_data, "hao_harbour_standard.png")
