import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="Hao Harbour 旗舰版-完美修复", layout="wide")

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
    
    # 极度严苛的 Prompt，防止 AI 话多
    prompt = (
        "你是一个英国房产文案专家。请精简原文，只输出以下 5 行内容，每行以 '-' 开头：\n"
        "1. 项目名称与位置\n"
        "2. 房型配置\n"
        "3. 租金（必须包含 £ 符号）\n"
        "4. 入住日期（起租时间）\n"
        "5. 核心亮点（一句话总结）\n"
        "严禁输出'长租类型'、'最短租期'、'押金'。严禁重复输出租金。\n\n"
        f"原文：{desc}"
    )
    
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

def draw_checkmark(draw, x, y, size=32, color=(40, 40, 40)):
    points = [(x, y + size//2), (x + size//3, y + size), (x + size, y)]
    draw.line(points, fill=color, width=6)

def add_safe_watermark(image, text):
    img = image.convert('RGBA')
    w, h = img.size
    txt_layer = Image.new('RGBA', (w, h), (255, 255, 255, 0))
    
    # 水印字体 220，颜色深 (透明度140)
    font = load_font(220)
    fill = (40, 40, 40, 140) 

    # 创建旋转文字块
    temp_draw = ImageDraw.Draw(txt_layer)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    
    txt_img = Image.new('RGBA', (tw + 100, th + 100), (255, 255, 255, 0))
    ImageDraw.Draw(txt_img).text((50, 50), text, font=font, fill=fill)
    
    # 旋转角度调小至 15 度，更安全
    rotated = txt_img.rotate(15, expand=True, resample=Image.BICUBIC)
    rw, rh = rotated.size

    # 放置两个绝对安全的位置
    # 第一个在图片区中心
    img_zone_h = h // 2
    pos1 = (w//2 - rw//2, img_zone_h//2 - rh//2)
    # 第二个在文字区中心
    pos2 = (w//2 - rw//2, img_zone_h + (h - img_zone_h)//2 - rh//2)

    txt_layer.paste(rotated, pos1, rotated)
    txt_layer.paste(rotated, pos2, rotated)
    return Image.alpha_composite(img, txt_layer)

def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    rows = (len(images) + 1) // 2
    
    poster = Image.new('RGB', (canvas_w, 5000), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 图片排列
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

    # 文案清洗，保留 £
    clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s,，.。\-\/£]', '', text)
    font = load_font(48)
    cur_y = rows * (img_h + gap) + 100
    
    for line in clean_text.split('\n'):
        line = line.strip()
        if not line: continue
        
        is_list = line.startswith('-')
        content = line.lstrip('- ').strip()
        
        # 针对长句子自动换行
        wrapped = textwrap.wrap(content, width=20 if is_list else 22)
        for idx, wl in enumerate(wrapped):
            if is_list and idx == 0:
                draw_checkmark(draw, 80, cur_y + 12)
                draw.text((140, cur_y), wl, fill=(30, 30, 30), font=font)
            else:
                indent = 140 if is_list else 80
                draw.text((indent, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 90
        cur_y += 20

    # 最后的精准裁剪：留一点底边美感
    final_poster = poster.crop((0, 0, canvas_w, cur_y + 100))
    # 加上深色居中水印
    watermarked = add_safe_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 Hao Harbour 海报最终修复版")
desc = st.text_area("粘贴 Description")
files = st.file_uploader("上传图片", accept_multiple_files=True)

if st.button("🚀 点击生成完美海报"):
    if desc and files:
        with st.spinner("正在修复文案与水印排版..."):
            poster_data = create_poster(files[:6], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("📥 下载海报", poster_data, "hao_harbour.png")
