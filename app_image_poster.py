import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import textwrap
import os
import re

st.set_page_config(page_title="Hao Harbour 8图旗舰版", layout="wide")

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
    
    # 强制中文提取，且条目不少于10条
    prompt = (
        "你是一个伦敦高端房产文案专家。请将房源信息提取为中文，要求内容丰富、专业，条目不少于12条：\n"
        "1. 标题：英文原名，如 'Lexington Gardens'。\n"
        "2. 详细列出：月租和周租（格式：月租XXXX磅，周租XXX磅）、房型、面积、入住日期。\n"
        "3. 交通与大学：详细列出步行至Nine Elms/Vauxhall站时间，及至KCL、LSE、UCL、IC等名校的地铁通勤时间。\n"
        "4. 大楼配套：详细列出24h礼宾、专属健身房、媒体室、商务中心、屋顶花园等设施。\n"
        "5. 生活环境：提到Battersea Power Station购物中心、泰晤士河径、周边超市（Waitrose/Sainsbury's）。\n"
        "要求：除标题外全部用中文，每行以 '√' 开头。严禁备注说明。确保所有英文单词完整不换行。\n\n"
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
    # 动态计算水印位置，均匀分布在海报中上部和中下部
    pos1 = (w//2 - rw//2, h//3 - rh//2)
    pos2 = (w//2 - rw//2, (h * 2)//3 - rh//2)
    txt_layer.paste(rotated, pos1, rotated)
    txt_layer.paste(rotated, pos2, rotated)
    return Image.alpha_composite(img, txt_layer)

def create_poster(images, text):
    canvas_w = 1200
    img_h = 450
    gap = 25
    # 最多显示8张图，2x4布局
    num_imgs = min(len(images), 8)
    rows = (num_imgs + 1) // 2
    
    # 预留足够的超长画布
    poster = Image.new('RGB', (canvas_w, 12000), (255, 255, 255))
    draw = ImageDraw.Draw(poster)
    
    # 1. 拼图区域 (2x4)
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

    # 2. 文案排版
    font = load_font(48)
    cur_y = rows * (img_h + gap) + 100
    
    # 增加宽度限制到 30，确保英文单词不被切断且利用横向空间
    max_width = 32
    
    # 过滤掉不需要的负面信息
    bad_keywords = ["最短租期", "押金", "说明", "备注"]
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    for line in lines:
        if any(k in line for k in bad_keywords): continue
        
        is_list = any(line.startswith(s) for s in ['√', '-', 'v', '*'])
        # 清理内容头部的符号
        content = re.sub(r'^[√\-v*]\s*', '', line)
        
        # 换行处理
        wrapped = textwrap.wrap(content, width=max_width, break_long_words=False)
        
        for idx, wl in enumerate(wrapped):
            current_x = 160 if is_list else 80
            if is_list and idx == 0:
                draw_checkmark(draw, 80, cur_y + 12)
            
            draw.text((current_x, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 95 # 增加行距，显得更大气
        cur_y += 20 # 段落间距

    # 3. 智能裁剪
    final_poster = poster.crop((0, 0, canvas_w, cur_y + 150))
    watermarked = add_smart_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 Hao Harbour 8图旗舰标准版")
st.markdown("这一版支持 **8张照片** 拼贴，且强化了**10+项中文亮点**提取。")
desc = st.text_area("粘贴 Description")
files = st.file_uploader("上传图片 (至少8张效果最佳)", accept_multiple_files=True)

if st.button("🚀 生成旗舰海报"):
    if desc and files:
        with st.spinner("正在提取海量房源亮点并排版..."):
            # 传入最多8张图
            poster_data = create_poster(files[:8], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("📥 下载海报", poster_data, "hao_harbour_flagship.png")
