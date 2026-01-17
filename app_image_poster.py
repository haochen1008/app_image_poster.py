import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="Hao Harbour 黄金标准模板 V2", layout="wide")

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
    
    # 强化 Prompt：深度挖掘交通、教育及设施配套，严格控制换行
    prompt = (
        "你是一位深耕伦敦Zone 1的高级房产经纪人。请根据描述完成以下内容的深度提取，模仿‘图10’的专业风格：\n"
        "1. 标题：仅显示英文原名，如 'Lexington Gardens'。确保简洁大气。\n"
        "2. 地理位置：详细描述 Nine Elms 核心区位，提到 SW11 邮编及泰晤士河南岸的优越性。\n"
        "3. 交通与通勤：基于 Nine Elms 或 Vauxhall 站，补充通勤至 KCL、LSE、UCL、IC 等名校的便利性，以及 Northern Line/Victoria Line 的连接性。\n"
        "4. 房型租金：月租与周租用逗号隔开，数字后加'磅'。列出精确面积和入住日期。\n"
        "5. 公寓配套：深挖24h礼宾、专属健身房、屋顶花园、私家媒体室等设施。\n"
        "6. 周边生活：提到 Battersea Power Station 购物中心、美国大使馆及泰晤士河径。\n"
        "要求：每行以 '√' 开头。严禁备注说明。英文单词必须完整。\n\n"
        f"原文：{desc}"
    )
    
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.4}
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
    poster = Image.new('RGB', (canvas_w, 10000), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 1. 拼图
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

    # 2. 文本逻辑
    font = load_font(48)
    cur_y = rows * (img_h + gap) + 100
    margin = 80
    
    # 增加可用宽度：调整换行参数以利用 London 后面的空白空间
    max_line_chars = 32 # 之前是 22，现在显著增加
    
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    for line in lines:
        is_list = line.startswith('√') or line.startswith('-')
        content = re.sub(r'^[√\-]\s*', '', line)
        
        # 使用更大的 width 值，并确保不截断单词
        wrapped = textwrap.wrap(content, width=max_line_chars, break_long_words=False)
        
        for idx, wl in enumerate(wrapped):
            current_x = 160 if is_list else 80
            if is_list and idx == 0:
                draw_checkmark(draw, 80, cur_y + 12)
            
            draw.text((current_x, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 90 # 行高
        cur_y += 15 # 段间距

    final_poster = poster.crop((0, 0, canvas_w, cur_y + 120))
    watermarked = add_smart_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 Hao Harbour 黄金标准 V2 (深度内容提取)")
desc = st.text_area("粘贴 Description (确保包含项目名称、邮编等关键信息)")
files = st.file_uploader("上传房源照片", accept_multiple_files=True)

if st.button("🚀 生成图10级别海报"):
    if desc and files:
        with st.spinner("正在进行深度内容提取与排版优化..."):
            poster_data = create_poster(files[:6], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("📥 下载海报", poster_data, "hao_harbour_pro.png")
