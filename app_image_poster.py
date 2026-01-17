import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap

# --- 页面配置 ---
st.set_page_config(page_title="高级房源海报生成器", layout="wide")

API_KEY = "sk-d99a91f22bf340139a335fb3d50d0ef5"
API_URL = "https://api.deepseek.com/chat/completions"

# --- 字体处理 (解决乱码的关键) ---
def get_font(size):
    # 尝试下载中文字体，如果下载失败则使用默认
    font_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansCJKsc/NotoSansCJKsc-Regular.ttf"
    try:
        r = requests.get(font_url)
        return ImageFont.truetype(io.BytesIO(r.content), size)
    except:
        return ImageFont.load_default()

def call_ai_summary(desc):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    prompt = f"你是一个房产专家。请根据以下描述，写一个极其精简的房源海报文案。要求：1. 标题吸睛。2. 列表式列出核心信息（位置、房型、租金、入住时间）。3. 全部中文，多用Emoji。不要有任何废话。\n\n原文：{desc}"
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

def create_poster(images, text):
    # 海报宽度固定
    canvas_w = 1200
    img_h = 450 # 每张图片的高度
    
    # 计算图片行数 (一行两张)
    num_imgs = len(images)
    rows = (num_imgs + 1) // 2
    total_img_h = rows * img_h
    
    # 创建画布
    canvas_h = total_img_h + 800 # 留出文字空间
    poster = Image.new('RGB', (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 1. 绘制图片 (1行2张)
    for i, img_file in enumerate(images):
        img = Image.open(img_file).convert("RGB")
        # 裁剪并缩放图片以适应 1/2 宽度
        target_w = canvas_w // 2 - 20
        img = img.resize((target_w, img_h), Image.Resampling.LANCZOS)
        
        x = 10 if i % 2 == 0 else canvas_w // 2 + 10
        y = (i // 2) * (img_h + 10) + 20
        poster.paste(img, (x, y))

    # 2. 绘制文案
    font_main = get_font(45)
    text_y = total_img_h + 60
    
    # 简单的自动换行处理
    margin = 60
    for line in text.split('\n'):
        wrapped_lines = textwrap.wrap(line, width=25) # 中文宽度限制
        for w_line in wrapped_lines:
            draw.text((margin, text_y), w_line, fill=(30, 30, 30), font=font_main)
            text_y += 70
        text_y += 20

    # 转为字节流供下载
    img_byte_arr = io.BytesIO()
    poster.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

# --- UI 界面 ---
st.title("🏡 高级房源海报合成器")
st.markdown("---")

col_in, col_out = st.columns([1, 1])

with col_in:
    st.subheader("1. 素材上传")
    desc = st.text_area("粘贴 Rightmove 描述", height=150)
    files = st.file_uploader("上传房源照片 (最多6张，1行2张排列)", accept_multiple_files=True, type=['jpg','png','jpeg'])
    if files:
        st.write(f"已选中 {len(files)} 张照片")

with col_out:
    st.subheader("2. 生成海报")
    if st.button("🎨 开始合成图片海报"):
        if not desc or not files:
            st.error("请确保填写了描述并上传了照片")
        else:
            with st.spinner("正在下载字体并合成海报..."):
                try:
                    # 1. AI 总结
                    summary = call_ai_summary(desc)
                    # 2. 合成图片
                    poster_data = create_poster(files[:6], summary)
                    # 3. 展示
                    st.image(poster_data)
                    st.download_button("📥 下载这张海报照片", poster_data, "property_poster.png", "image/png")
                except Exception as e:
                    st.error(f"失败了: {e}")
