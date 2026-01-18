import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="Hao Harbour 旗舰定型版", layout="wide")

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
    
    prompt = (
        "你是一个伦敦高端房产文案专家。请将房源信息提取为中文，条目不少于12条：\n"
        "1. 标题：英文原名，如 'Lexington Gardens'。\n"
        "2. 租金：月租与周租（格式：月租XXXX磅，周租XXX磅）。\n"
        "3. 房型面积：间数、双卫配置、具体面积及入住日期。\n"
        "4. 交通通勤：邻近地铁站名，并说明可便捷通勤至 LSE, KCL, UCL, IC, King's College 等名校（严禁写具体分钟数）。\n"
        "5. 大楼设施：详细列出24h礼宾、健身房、影音室、私人阳台、屋顶花园等。\n"
        "6. 生活环境：周边高端超市、购物中心及景观步道。\n"
        "要求：除标题外全部用中文，每行以 '√' 开头。严禁备注说明。确保所有英文单词完整且不换行。\n\n"
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
    # 水印加深：Alpha 调至 190
    fill = (40, 40, 40, 190) 
    temp_draw = ImageDraw.Draw(txt_layer)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    txt_img = Image.new('RGBA', (tw + 100, th + 100), (255, 255, 255, 0))
    ImageDraw.Draw(txt_img).text((50, 50), text, font=font, fill=fill)
    rotated = txt_img.rotate(18, expand=True, resample=Image.BICUBIC)
    rw, rh = rotated.size
    pos1 = (w//2 - rw//2, h//3 - rh//2)
    pos2 = (w//2 - rw//2, (h * 2)//3 - rh//2)
    txt_layer.paste(rotated, pos1, rotated)
    txt_layer.paste(rotated, pos2, rotated)
    return Image.alpha_composite(img, txt_layer)

def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    num_imgs = min(len(images), 8)
    rows = (num_imgs + 1) // 2
    
    poster = Image.new('RGB', (canvas_w, 12000), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 1. 拼图区域 (2x4 布局)
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

    # 2. 文本排版核心修正
    font = load_font(48)
    cur_y = rows * (img_h + gap) + 120
    
    # 【极重要】物理防截断参数
    # 降低 width 阈值到 20 左右，确保在 1200px 宽度内即使单词再长也有余地
    safe_char_width = 20 
    left_margin = 100
    text_x_start = 180
    
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    for line in lines:
        if any(k in line for k in ["最短租期", "押金", "备注"]): continue
        
        is_list = any(line.startswith(s) for s in ['√', '-', 'v', '*'])
        content = re.sub(r'^[√\-v*]\s*', '', line)
        
        # 强制换行计算：禁止切断长单词
        wrapped = textwrap.wrap(content, width=safe_char_width, break_long_words=False)
        
        for idx, wl in enumerate(wrapped):
            render_x = text_x_start if is_list else left_margin
            if is_list and idx == 0:
                draw_checkmark(draw, left_margin, cur_y + 12)
            
            draw.text((render_x, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 90 
        cur_y += 25 

    final_poster = poster.crop((0, 0, canvas_w, cur_y + 150))
    watermarked = add_smart_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- Streamlit UI ---
st.title("🏡 Hao Harbour 旗舰旗舰修正版")
st.markdown("✅ **水印颜色加深** | ✅ **右侧绝对防截断** | ✅ **中文8图深度提取**")
desc = st.text_area("粘贴 Description")
files = st.file_uploader("上传图片 (前8张生效)", accept_multiple_files=True)

if st.button("🚀 生成高清海报"):
    if desc and files:
        with st.spinner("正在生成..."):
            poster_data = create_poster(files[:8], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("📥 下载海报", poster_data, "hao_harbour_final.png")
