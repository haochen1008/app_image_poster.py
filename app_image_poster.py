import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os
import re

st.set_page_config(page_title="Hao Harbour 海报", layout="wide")

def load_font(size):
    # 尝试加载中文字体，若无则使用默认
    font_paths = ["simhei.ttf", "msyh.ttc", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    for path in font_paths:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except: continue
    return ImageFont.load_default()

def call_ai_summary(desc):
    API_KEY = "sk-d99a91f22bf340139a335fb3d50d0ef5"
    API_URL = "https://api.deepseek.com/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    # 提示词要求：保留英文原名的地铁站、地址和线路，不翻译
    prompt = (
        "你是一个伦敦高端房产文案专家。请将房源信息提取为中文，要求内容丰富并遵循以下准则：\n"
        "1. 标题：英文原名 (例如 Lexington Gardens)。\n"
        "2. 租金：月租和周租 (格式：月租XXXX磅，周租XXX磅)。\n"
        "3. 地理位置与交通：保留英文原名，不要翻译地址、地铁站名和地铁线名 (例如 Nine Elms, Vauxhall Station, Northern Line)。\n"
        "4. 通勤描述：列举可通勤的高校 (LSE, KCL, UCL, IC, King's College)，禁止写具体分钟数。\n"
        "5. 大楼设施与周边：详细描述24h礼宾、健身房、屋顶花园等，条目总数不少于12条。\n"
        "要求：每行以 '√' 开头。专有名词不翻译。严禁备注说明。\n\n"
        f"原文：{desc}"
    )
    
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
    try:
        res = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        return res.json()['choices'][0]['message']['content']
    except:
        return "提取失败，请重试。"

def draw_checkmark(draw, x, y, size=32, color=(30, 30, 30)):
    points = [(x, y + size//2), (x + size//3, y + size), (x + size, y)]
    draw.line(points, fill=color, width=6)

def add_deep_watermark(image, text):
    img = image.convert('RGBA')
    w, h = img.size
    txt_layer = Image.new('RGBA', (w, h), (255, 255, 255, 0))
    font = load_font(240)
    # 显著加深：Alpha 调至 220 (接近不透明)
    fill = (20, 20, 20, 220) 
    
    temp_draw = ImageDraw.Draw(txt_layer)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    
    txt_img = Image.new('RGBA', (tw + 100, th + 100), (255, 255, 255, 0))
    ImageDraw.Draw(txt_img).text((50, 50), text, font=font, fill=fill)
    rotated = txt_img.rotate(22, expand=True, resample=Image.BICUBIC)
    
    rw, rh = rotated.size
    # 在海报上中下均匀分布三层深色水印
    for i in range(1, 4):
        pos = (w//2 - rw//2, (h * i)//4 - rh//2)
        txt_layer.paste(rotated, pos, rotated)
    
    return Image.alpha_composite(img, txt_layer)

def pixel_wrap(text, font, max_pixel_width):
    """
    强制物理折行：不论是否为单词，只要超过宽度即换行。
    """
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        w = font.getlength(test_line)
        if w <= max_pixel_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
    lines.append(current_line)
    return lines

def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    num_imgs = min(len(images), 8)
    rows = (num_imgs + 1) // 2
    
    poster = Image.new('RGB', (canvas_w, 15000), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 1. 8张照片拼图 (2x4)
    for i in range(num_imgs):
        img = Image.open(images[i]).convert("RGB")
        tw = (canvas_w - gap * 3) // 2
        scale = max(tw/img.width, img_h/img.height)
        img = img.resize((int(img.width*scale), int(img.height*scale)), Image.Resampling.LANCZOS)
        left, top = (img.width-tw)/2, (img.height-img_h)/2
        img = img.crop((left, top, left+tw, top+img_h))
        x = gap if i % 2 == 0 else tw + gap * 2
        y = (i // 2) * (img_h + gap) + gap
        poster.paste(img, (x, y))

    # 2. 文案排版 (物理防截断)
    font = load_font(48)
    cur_y = rows * (img_h + gap) + 120
    
    left_margin = 100
    text_x_start = 180
    # 设置可渲染的最大宽度为 920 像素 (留出约 280 像素的右边距防止溢出)
    max_w = 920 
    
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    for line in lines:
        if any(k in line for k in ["最短租期", "押金", "说明"]): continue
        
        is_list = line.startswith('√')
        content = re.sub(r'^[√\-v*]\s*', '', line)
        
        # 使用像素换行逻辑
        wrapped_parts = pixel_wrap(content, font, max_w)
        
        for idx, part in enumerate(wrapped_parts):
            render_x = text_x_start if is_list else left_margin
            if is_list and idx == 0:
                draw_checkmark(draw, left_margin, cur_y + 12)
            
            draw.text((render_x, cur_y), part, fill=(35, 35, 35), font=font)
            cur_y += 90 
        cur_y += 25 

    # 3. 裁剪与深度水印
    final_poster = poster.crop((0, 0, canvas_w, cur_y + 150))
    watermarked = add_deep_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI 面板 ---
st.title("🏡 Hao Harbour 海报")
st.markdown("✅ **水印加深** | ✅ **物理级防截断** | ✅ **地址地铁不翻译** | ✅ **8张图排版**")

desc = st.text_area("粘贴房源 Description")
files = st.file_uploader("上传图片 (前8张生效)", accept_multiple_files=True)

if st.button("🚀 生成定稿海报"):
    if desc and files:
        with st.spinner("正在精准提取并排版..."):
            poster_data = create_poster(files[:8], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("📥 下载海报", poster_data, "hao_harbour_final.png")
