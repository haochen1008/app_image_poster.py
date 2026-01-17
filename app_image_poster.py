import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="Hao Harbour 旗舰标准模板", layout="wide")

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
    
    # 强化 Prompt：锁定丰富内容提取，禁用中文地址翻译
    prompt = (
        "你是一个高端房产文案专家。请提取房源详情。要求：\n"
        "1. 标题直接使用英文原名，如 'Lexington Gardens'，不要翻译成中文名。\n"
        "2. 详细列出：地理位置、房型配置、租金（格式为：月租XXXX磅，周租XXX磅）、面积、入住日期。\n"
        "3. 详细列出公寓亮点（设施、交通、周边）。\n"
        "4. 每一项信息必须以 '-' 开头。\n"
        "5. 严禁输出'最短租期'、'文案说明'或'备注'。\n"
        "6. 确保英文单词如 Vauxhall, Lexington Gardens 完整出现。\n\n"
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
    fill = (40, 40, 40, 140) # 深色加重水印

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
    
    # 1. 图片拼贴
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

    # 2. 文本清洗
    lines = text.split('\n')
    # 强制拦截不需要的信息
    bad_keywords = ["最短租期", "文案说明", "备注", "押金"]
    filtered_lines = [l for l in lines if not any(k in l for k in bad_keywords)]
    clean_text = "\n".join(filtered_lines)
    
    font = load_font(48)
    cur_y = rows * (img_h + gap) + 100
    
    # 3. 渲染文案
    for line in clean_text.split('\n'):
        line = line.strip()
        if not line: continue
        
        is_list = line.startswith('-')
        content = line.lstrip('- ').strip()
        
        # --- 核心改进：大幅增加 width，防止英文单词折断 ---
        # 40个半角字符的宽度足够容纳绝大多数长单词
        wrapped = textwrap.wrap(content, width=35 if is_list else 40, break_long_words=False)
        
        for idx, wl in enumerate(wrapped):
            current_x = 140 if is_list else 80
            if is_list and idx == 0:
                draw_checkmark(draw, 80, cur_y + 12)
            
            # 渲染文字
            draw.text((current_x, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 90
        cur_y += 15

    # 4. 动态裁剪与水印
    final_poster = poster.crop((0, 0, canvas_w, cur_y + 120))
    watermarked = add_smart_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 Hao Harbour 旗舰海报模板 (Vauxhall 单词保护版)")
desc = st.text_area("粘贴房源 Description")
files = st.file_uploader("上传图片 (建议6张)", accept_multiple_files=True)

if st.button("🚀 生成标准海报"):
    if desc and files:
        with st.spinner("正在按模板提取精华内容..."):
            poster_data = create_poster(files[:6], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("📥 下载海报", poster_data, "hao_harbour_poster.png")
