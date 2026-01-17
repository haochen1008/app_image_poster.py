import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap

st.set_page_config(page_title="高级房源海报合成器", layout="wide")

API_KEY = "sk-d99a91f22bf340139a335fb3d50d0ef5"
API_URL = "https://api.deepseek.com/chat/completions"

# --- 1. 核心修复：自动下载字体以解决乱码 ---
@st.cache_data
def load_font(size):
    # 从网络下载 Noto Sans 字体（Google开源），确保云端环境也能显示中文
    font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
    try:
        response = requests.get(font_url)
        return ImageFont.truetype(io.BytesIO(response.content), size)
    except:
        # 如果下载失败，退回到系统默认（可能会乱码，但在本地运行通常没问题）
        return ImageFont.load_default()

def call_ai_summary(desc):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    prompt = f"你是一个房产专家。请根据提供的房源描述，写一个极其精简的文案。要求：1.标题吸睛。2.列表式列出核心信息（位置、房型、租金、入住时间）。3.全部中文，多用Emoji。不要有任何废话。\n\n原文：{desc}"
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 2. 核心布局：1行2张图片，支持6张图 ---
def create_poster(images, text):
    canvas_w = 1200
    img_h = 450  # 每张照片的高度
    gap = 20     # 照片之间的间隙
    
    num_imgs = len(images)
    rows = (num_imgs + 1) // 2
    total_img_h = rows * (img_h + gap)
    
    # 画布预留底部1000像素用于写文案
    canvas_h = total_img_h + 1000
    poster = Image.new('RGB', (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 放置图片 (1行2张)
    for i, img_file in enumerate(images):
        img = Image.open(img_file).convert("RGB")
        target_w = (canvas_w - gap * 3) // 2
        # 居中裁剪缩放
        w_ratio = target_w / img.width
        h_ratio = img_h / img.height
        ratio = max(w_ratio, h_ratio)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # 裁剪到固定尺寸
        left = (img.width - target_w) / 2
        top = (img.height - img_h) / 2
        img = img.crop((left, top, left + target_w, top + img_h))
        
        x = gap if i % 2 == 0 else target_w + gap * 2
        y = (i // 2) * (img_h + gap) + gap
        poster.paste(img, (x, y))

    # 绘制文案
    font_main = load_font(42)
    text_y = total_img_h + 80
    margin = 80
    
    # 绘制背景装饰线（可选）
    draw.line((margin, text_y - 20, canvas_w - margin, text_y - 20), fill=(200, 200, 200), width=2)
    
    for line in text.split('\n'):
        wrapped_lines = textwrap.wrap(line, width=28) # 针对42号字体的自动换行
        for w_line in wrapped_lines:
            draw.text((margin, text_y), w_line, fill=(40, 40, 40), font=font_main)
            text_y += 65
        text_y += 15

    # 裁剪画布多余的留白
    final_poster = poster.crop((0, 0, canvas_w, text_y + 100))
    img_byte_arr = io.BytesIO()
    final_poster.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

# --- 3. UI 逻辑 ---
st.title("🏡 精英房源海报合成器")
st.markdown("---")

col_in, col_out = st.columns([1, 1])

with col_in:
    st.subheader("素材输入")
    desc = st.text_area("粘贴房源 Description", height=200, placeholder="粘贴 Rightmove 描述...")
    files = st.file_uploader("上传房源照片 (1-6张)", accept_multiple_files=True, type=['jpg','png','jpeg'])

with col_out:
    st.subheader("海报预览")
    if st.button("🎨 一键生成海报图片"):
        if desc and files:
            with st.spinner("正在加载字体并生成精简版海报..."):
                try:
                    # 获取精简版文案
                    summary = call_ai_summary(desc)
                    # 合成图片 (只取前6张)
                    poster_data = create_poster(files[:6], summary)
                    st.image(poster_data)
                    st.download_button("📥 下载海报照片", poster_data, "poster.png", "image/png")
                except Exception as e:
                    st.error(f"生成失败，请检查网络或余额。错误内容：{e}")
        else:
            st.warning("请先上传照片并粘贴描述")
