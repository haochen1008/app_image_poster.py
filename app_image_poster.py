import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os
import re

st.set_page_config(page_title="Hao Harbour 旗舰定型版", layout="wide")

def load_font(size):
    # 优先加载中文字体
    font_paths = ["simhei.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    for path in font_paths:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except: continue
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
        "4. 交通通勤：邻近地铁站名，列举可便捷通勤至 LSE, KCL, UCL, IC, King's College 等名校。\n"
        "5. 大楼设施：24h礼宾、健身房、影音室、私人阳台、屋顶花园等。\n"
        "6. 生活环境：周边超市、购物中心及景观步道。\n"
        "要求：除标题外全部用中文，每行以 '√' 开头。不含备注，禁止写具体通勤分钟数。\n\n"
        f"原文：{desc}"
    )
    
    try:
        payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
        res = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        return res.json()['choices'][0]['message']['content']
    except:
        return "提取失败，请检查 API 或网络。"

def draw_checkmark(draw, x, y, size=32, color=(40, 40, 40)):
    points = [(x, y + size//2), (x + size//3, y + size), (x + size, y)]
    draw.line(points, fill=color, width=6)

def add_deep_watermark(image, text):
    img = image.convert('RGBA')
    w, h = img.size
    txt_layer = Image.new('RGBA', (w, h), (255, 255, 255, 0))
    font = load_font(220)
    # 水印颜色深度大幅提升 (Alpha=210, 接近不透明)
    fill = (20, 20, 20, 210) 
    
    temp_draw = ImageDraw.Draw(txt_layer)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    
    txt_img = Image.new('RGBA', (tw + 100, th + 100), (255, 255, 255, 0))
    ImageDraw.Draw(txt_img).text((50, 50), text, font=font, fill=fill)
    rotated = txt_img.rotate(20, expand=True, resample=Image.BICUBIC)
    
    rw, rh = rotated.size
    # 增加水印覆盖频率
    positions = [(w//2 - rw//2, h//4 - rh//2), (w//2 - rw//2, h//2 - rh//2), (w//2 - rw//2, 3*h//4 - rh//2)]
    for pos in positions:
        txt_layer.paste(rotated, pos, rotated)
    
    return Image.alpha_composite(img, txt_layer)

def smart_wrap(text, font, max_width):
    """
    暴力折行逻辑：不考虑单词完整性，只要到边界就换行。
    """
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        bbox = font.getbbox(test_line)
        if bbox[2] <= max_width:
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

    # 2. 文本逻辑 (关键修正：允许折行)
    font = load_font(48)
    cur_y = rows * (img_h + gap) + 120
    
    left_margin = 100
    text_x_start = 180
    # 允许的文字渲染最大宽度 (canvas_w - 边距 - 右侧安全区)
    max_render_w = 900 
    
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    for line in lines:
        if any(k in line for k in ["最短租期", "押金", "备注"]): continue
        
        is_list = line.startswith('√')
        content = re.sub(r'^[√\-v*]\s*', '', line)
        
        # 使用暴力折行函数代替 textwrap
        wrapped_lines = smart_wrap(content, font, max_render_w)
        
        for idx, wl in enumerate(wrapped_lines):
            render_x = text_x_start if is_list else left_margin
            if is_list and idx == 0:
                draw_checkmark(draw, left_margin, cur_y + 12)
            
            draw.text((render_x, cur_y), wl, fill=(30, 30, 30), font=font)
            cur_y += 90 
        cur_y += 25 

    final_poster = poster.crop((0, 0, canvas_w, cur_y + 150))
    watermarked = add_deep_watermark(final_poster, "Hao Harbour")
    
    buf = io.BytesIO()
    watermarked.convert('RGB').save(buf, format='PNG')
    return buf.getvalue()

# --- UI ---
st.title("🏡 Hao Harbour 旗舰旗舰修正版")
st.markdown("✅ **水印显著加深** | ✅ **全字符折行保护(杜绝截断)** | ✅ **中文8图深度提取**")
desc = st.text_area("粘贴房源描述")
files = st.file_uploader("上传图片 (前8张生效)", accept_multiple_files=True)

if st.button("🚀 生成海报"):
    if desc and files:
        with st.spinner("正在生成..."):
            poster_data = create_poster(files[:8], call_ai_summary(desc))
            st.image(poster_data)
            st.download_button("📥 下载海报", poster_data, "hao_harbour_final.png")
