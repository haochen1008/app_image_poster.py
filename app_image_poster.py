import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="Hao Harbour 旗舰丰富版", layout="wide")

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
    
    # 调整 Prompt：要求丰富、保留关键数据，强制使用 £
    prompt = (
        "你是一个高端房产文案专家。请根据描述写一份详尽的海报文案。要求：\n"
        "1. 标题要大气吸睛。\n"
        "2. 详细列出：地理位置（邮编、区位）、房型配置（卧室/卫浴/阳台）、租金详情（必须同时包含月租和周租，使用 £ 符号）、面积大小、入住日期。\n"
        "3. 详细列出公寓亮点（如24小时礼宾、健身房、媒体室、交通枢纽、周边公园等）。\n"
        "4. 每一项信息必须以 'v' 或 '-' 开头，排版整齐。\n"
        "5. 严禁输出'最短租期'、'押金'。租金信息只输出一次，不要重复。\n\n"
        f"原文：{desc}"
    )
    
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.4}
    res = requests.post(API_URL, headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

def draw_checkmark(draw, x, y, size=32, color=(40, 40, 40)):
    # 绘制更美观的 V 字勾号
    points = [(x, y + size//2), (x + size//3, y + size), (x + size, y)]
    draw.line(points, fill=color, width=6)

def add_smart_watermark(image, text):
    img = image.convert('RGBA')
    w, h = img.size
    txt_layer = Image.new('RGBA', (w, h), (255, 255, 255, 0))
    
    font = load_font(220) # 大号字体
    fill = (40, 40, 40, 140) # 深色透明度

    # 创建文字块
    temp_draw = ImageDraw.Draw(txt_layer)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    txt_img = Image.new('RGBA', (tw + 100, th + 100), (255, 255, 255, 0))
    ImageDraw.Draw(txt_img).text((50, 50), text, font=font, fill=fill)
    
    # 旋转 18 度，美观且安全
    rotated = txt_img.rotate(18, expand=True, resample=Image.BICUBIC)
    rw, rh = rotated.size

    # 第一个水印：图片拼贴区中心
    # 假设图片占了一半左右的高度
    pos1 = (w//2 - rw//2, h//4 - rh//2)
    # 第二个水印：文字描述区中心
    # 文字区是从图片结束到海报底部
    pos2 = (w//2 - rw//2, (h * 3)//4 - rh//2)

    txt_layer.paste(rotated, pos1, rotated)
    txt_layer.paste(rotated, pos2, rotated)
    return Image.alpha_composite(img, txt_layer)

def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    rows = (len(images) + 1) // 2
    
    # 预设一个足够长的画布
    poster = Image.new('RGB', (canvas_w, 6000), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 1. 拼图区域
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

    # 2. 文案排版区域
    # 正则表达式增强：明确放行 £ 符号
    clean_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s,，.。\-\/£v√:：]', '', text)
    font = load_font(48)
    cur_y = rows * (img_h + gap) + 80
    
    lines = clean_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # 判断是否为列表项（支持 AI 输出的 - 或 v 或 √）
        is_list = any(line.startswith(s) for s in ['-', 'v', '√'])
        content = line.lstrip('-v√ ').strip()
        
        wrapped = textwrap.wrap(content, width=22 if is_list else 24)
        for idx, wl in enumerate(wrapped):
            if is_list and idx == 0:
                draw_checkmark(draw, 80, cur_y + 12)
                draw.text((140, cur_y), wl, fill=(30, 30, 30), font=font)
            else:
                indent = 140 if is_list else 80
                draw.text((indent, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 90
        cur_y += 15

    # 3. 精准裁剪与水印
    final_poster = poster.crop((0, 0, canvas_w, cur_y + 120))
    watermarked = add_smart_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 Hao Harbour 旗舰丰富版")
st.markdown("这一版强化了**文案丰富度**、**£符号保留**以及**水印位置适配**。")
desc = st.text_area("粘贴 Description")
files = st.file_uploader("上传图片", accept_multiple_files=True)

if st.button("🚀 生成海报"):
    if desc and files:
        with st.spinner("正在生成内容丰富的海报..."):
            poster_data = create_poster(files[:6], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("📥 下载海报", poster_data, "hao_harbour_full.png")
