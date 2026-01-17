import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

# 页面基本设置
st.set_page_config(page_title="房源海报合成器-字体修复版", layout="wide")

# --- 核心：字体加载逻辑 ---
def load_font(size):
    # 路径：这是你上传到 GitHub 的文件
    font_path = "simhei.ttf"
    
    if os.path.exists(font_path):
        try:
            # 尝试加载
            return ImageFont.truetype(font_path, size)
        except Exception as e:
            st.error(f"字体加载失败，虽然文件存在。错误：{e}")
    
    st.warning("⚠️ 未检测到本地 simhei.ttf，将尝试下载。若仍乱码请检查 GitHub 上传情况。")
    # 备用方案：下载
    try:
        font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
        r = requests.get(font_url, timeout=10)
        return ImageFont.truetype(io.BytesIO(r.content), size)
    except:
        return ImageFont.load_default()

def call_ai_summary(desc):
    API_KEY = "sk-d99a91f22bf340139a335fb3d50d0ef5"
    API_URL = "https://api.deepseek.com/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    # 强制 AI 严禁使用任何加粗或标题符号，避免干扰图片渲染
    prompt = f"你是一个专业的房产中介。请根据描述写一个极其精简的海报文案。要求：1.标题吸睛。2.列表式列出核心信息（位置、房型、租金、入住时间）。3.全部中文，多用Emoji。严禁输出任何 ** 或 # 等 Markdown 符号。\n\n原文：{desc}"
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

def create_poster(images, text):
    canvas_w = 1200
    img_h = 450  # 每张照片的高度
    gap = 25     # 照片间隙
    
    num_imgs = len(images)
    rows = (num_imgs + 1) // 2
    total_img_h = rows * (img_h + gap)
    
    # 建立大画布
    poster = Image.new('RGB', (canvas_w, total_img_h + 1200), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 1. 拼图排版 (1行2张)
    for i, img_file in enumerate(images):
        img = Image.open(img_file).convert("RGB")
        target_w = (canvas_w - gap * 3) // 2
        # 裁剪缩放
        scale = max(target_w/img.width, img_h/img.height)
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        left = (img.width - target_w) / 2
        top = (img.height - img_h) / 2
        img = img.crop((left, top, left + target_w, top + img_h))
        
        x = gap if i % 2 == 0 else target_w + gap * 2
        y = (i // 2) * (img_h + gap) + gap
        poster.paste(img, (x, y))

    # 2. 文案绘制 (清洗 Markdown)
    clean_text = re.sub(r'[*#_~`>]', '', text) 
    font = load_font(42)
    current_y = total_img_h + 80
    margin = 80
    
    for line in clean_text.split('\n'):
        line = line.strip()
        if not line:
            current_y += 30
            continue
        # 自动换行
        wrapped = textwrap.wrap(line, width=24)
        for w_line in wrapped:
            draw.text((margin, current_y), w_line, fill=(40, 40, 40), font=font)
            current_y += 70
        current_y += 15

    # 裁剪掉多余的白色底部
    return poster.crop((0, 0, canvas_w, current_y + 100))

# --- Streamlit UI ---
st.title("🖼️ 房源海报自动生成器 (本地字体增强版)")
st.markdown("---")

desc_in = st.text_area("1. 粘贴 Rightmove 描述", height=200)
files_in = st.file_uploader("2. 上传房源照片 (最多6张)", accept_multiple_files=True)

if st.button("🚀 生成海报图片"):
    if desc_in and files_in:
        with st.spinner("AI 正在提炼精简文案并合成海报..."):
            try:
                summary = call_ai_summary(desc_in)
                poster_img = create_poster(files_in[:6], summary)
                
                # 展示预览
                st.image(poster_img, caption="生成成功！请点击下方按钮下载。")
                
                # 转换为下载格式
                buf = io.BytesIO()
                poster_img.save(buf, format='PNG')
                st.download_button("📥 下载海报照片", buf.getvalue(), "house_poster.png", "image/png")
            except Exception as e:
                st.error(f"发生错误: {e}")
    else:
        st.warning("请检查：描述是否粘贴？照片是否上传？")
