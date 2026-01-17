import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os

st.set_page_config(page_title="房源海报合成器-无乱码版", layout="wide")

API_KEY = "sk-d99a91f22bf340139a335fb3d50d0ef5"
API_URL = "https://api.deepseek.com/chat/completions"

# --- 核心改进：多重保障加载字体 ---
def load_font(size):
    # 路径 A: 你上传到 GitHub 的本地字体文件
    local_font_path = "simhei.ttf"
    # 路径 B: 系统自带的可能路径
    system_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "C:/Windows/Fonts/simhei.ttf"
    ]
    
    if os.path.exists(local_font_path):
        return ImageFont.truetype(local_font_path, size)
    
    for path in system_fonts:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
            
    # 如果都找不到，尝试紧急在线下载
    try:
        font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
        r = requests.get(font_url, timeout=5)
        return ImageFont.truetype(io.BytesIO(r.content), size)
    except:
        return ImageFont.load_default()

def call_ai_summary(desc):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    prompt = f"你是一个房产专家。请根据提供的房源描述，写一个精简的海报文案。要求：1.标题吸睛。2.列表式列出核心信息（位置、房型、租金、入住时间）。3.全部中文，多用Emoji。不要有任何废话。\n\n原文：{desc}"
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

def create_poster(images, text):
    canvas_w = 1200
    img_h = 450  # 每张图高度
    gap = 20     # 间隙
    
    num_imgs = len(images)
    rows = (num_imgs + 1) // 2
    total_img_h = rows * (img_h + gap)
    
    poster = Image.new('RGB', (canvas_w, total_img_h + 1000), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 图片排列：1行2张
    for i, img_file in enumerate(images):
        img = Image.open(img_file).convert("RGB")
        target_w = (canvas_w - gap * 3) // 2
        
        # 居中裁剪缩放逻辑
        scale = max(target_w/img.width, img_h/img.height)
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        left = (img.width - target_w) / 2
        top = (img.height - img_h) / 2
        img = img.crop((left, top, left + target_w, top + img_h))
        
        x = gap if i % 2 == 0 else target_w + gap * 2
        y = (i // 2) * (img_h + gap) + gap
        poster.paste(img, (x, y))

    # 文案绘制
    font = load_font(42)
    current_y = total_img_h + 80
    margin = 80
    
    # 处理 DeepSeek 返回的特殊字符
    clean_text = text.replace("**", "").replace("#", "")
    
    for line in clean_text.split('\n'):
        if not line.strip(): continue
        wrapped = textwrap.wrap(line, width=25)
        for w_line in wrapped:
            draw.text((margin, current_y), w_line, fill=(40, 40, 40), font=font)
            current_y += 65
        current_y += 10

    # 自动裁剪底部
    final_poster = poster.crop((0, 0, canvas_w, current_y + 100))
    buf = io.BytesIO()
    final_poster.save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 房源海报合成器（修正版）")

col_in, col_out = st.columns([1, 1])
with col_in:
    desc = st.text_area("粘贴 Description", height=200)
    files = st.file_uploader("上传照片 (1-6张)", accept_multiple_files=True)

with col_out:
    if st.button("🎨 生成无乱码海报"):
        if desc and files:
            with st.spinner("正在合成..."):
                summary = call_ai_summary(desc)
                poster_data = create_poster(files[:6], summary)
                st.image(poster_data)
                st.download_button("📥 下载海报", poster_data, "poster.png")
