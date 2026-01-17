import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import textwrap # 用于文字自动换行
import base64 # 用于处理图片URL

# 页面配置
st.set_page_config(page_title="AI图片海报生成器", layout="wide", page_icon="🖼️")

# DeepSeek API 配置 (用于AI总结，如果需要)
API_KEY = "sk-d99a91f22bf340139a335fb3d50d0ef5"
API_URL = "https://api.deepseek.com/chat/completions"

def call_ai_summarize(desc_text):
    if not desc_text:
        return "请提供描述文字。"
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    prompt = f"""
    你是一个专业的英国房产中介。请根据以下描述，为客户生成一份简洁的中文房源核心要点。
    要求：总结3-5个最关键的卖点，包括位置、房型、租金、交通、亮点等。
    请直接输出总结内容，不要带任何前缀或解释性文字。
    
    原始描述：
    {desc_text}
    """
    
    payload = {
        "model": "deepseek-chat", # 使用deepseek-chat进行文本总结
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 300
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        st.error(f"AI总结失败，请检查DeepSeek余额或网络。错误：{e}")
        return "AI总结失败，请手动编辑。"

def get_font(size, is_bold=False):
    # Streamlit Cloud 环境下的字体路径可能需要调整
    # 尝试使用默认字体或更通用的字体
    font_path = "arial.ttf" # Windows默认
    try:
        return ImageFont.truetype(font_path, size)
    except IOError:
        try: # 尝试Linux/Mac默认字体
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except IOError:
            return ImageFont.load_default() # Fallback到默认字体

def create_property_poster(images, description_summary):
    if not images:
        st.error("没有上传图片，无法生成海报。")
        return None

    # 海报尺寸 (可调整)
    poster_width = 1080 # 常见社交媒体图片宽度
    single_image_height = 400 # 每张图高度
    text_area_height = 300 # 文字区域高度
    
    # 动态计算海报总高度
    total_image_height = len(images) * single_image_height
    poster_height = total_image_height + text_area_height + 50 # 额外留白

    poster = Image.new('RGB', (poster_width, poster_height), color = 'white')
    draw = ImageDraw.Draw(poster)

    # 1. 放置图片
    current_y = 0
    for img_file in images:
        try:
            img = Image.open(img_file).convert("RGB")
            img = img.resize((poster_width, single_image_height), Image.LANCZOS)
            poster.paste(img, (0, current_y))
            current_y += single_image_height
        except Exception as e:
            st.warning(f"无法加载图片: {img_file.name if hasattr(img_file, 'name') else '未知文件'}. 错误: {e}")
            continue

    # 2. 放置文字
    text_margin = 40
    text_x = text_margin
    text_y = current_y + text_margin

    # 标题字体
    title_font = get_font(38, is_bold=True)
    draw.text((text_x, text_y), "✨ 精选房源推荐 ✨", fill=(50, 50, 50), font=title_font)
    text_y += 60

    # 内容字体
    content_font = get_font(28)
    # 自动换行
    lines = textwrap.wrap(description_summary, width=45) # 每行45个字符左右
    for line in lines:
        draw.text((text_x, text_y), line, fill=(70, 70, 70), font=content_font)
        text_y += 40 # 行间距

    # 3. 生成可下载的图片数据
    buf = BytesIO()
    poster.save(buf, format="PNG") # PNG格式支持透明背景，JPG适合照片
    byte_im = buf.getvalue()
    return byte_im

# --- Streamlit UI ---
st.title("🖼️ 房源图片海报生成器 (BETA)")
st.markdown("---")
st.info("💡 操作指南：上传2-3张房源图片，粘贴描述，AI将自动总结并生成一张可下载的图片海报！")

# 1. 上传图片
st.subheader("1️⃣ 上传房源图片 (建议2-3张，最多5张)")
uploaded_files = st.file_uploader("支持 JPG/PNG 格式", accept_multiple_files=True, type=['jpg', 'png', 'jpeg'])

# 2. 粘贴描述
st.subheader("2️⃣ 粘贴房源描述")
desc_text = st.text_area("从 Rightmove 复制 Description 到这里...", height=180)

# 3. 生成海报按钮
if st.button("✨ 生成海报图片"):
    if not uploaded_files:
        st.error("请至少上传一张图片！")
    elif not desc_text:
        st.error("请粘贴房源描述！")
    else:
        with st.spinner("AI 正在总结描述并合成图片海报中..."):
            # 限制最多处理5张图片，避免内存过载
            selected_images = uploaded_files[:5]
            
            # AI 总结描述
            summary = call_ai_summarize(desc_text)
            
            # 合成图片海报
            image_bytes = create_property_poster(selected_images, summary)
            
            if image_bytes:
                st.success("海报生成成功！")
                st.image(image_bytes, caption="您的专属房源海报", use_column_width=True)
                
                # 提供下载按钮
                st.download_button(
                    label="⬇️ 下载海报图片",
                    data=image_bytes,
                    file_name="房源海报.png",
                    mime="image/png"
                )
                st.balloons()
            else:
                st.error("海报生成失败，请检查上传图片或描述内容。")

st.markdown("---")
st.caption("注意：此功能处于测试阶段，图片处理可能消耗更多资源。")
