import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import requests
import io
import os
import re
import pandas as pd
from datetime import datetime

# --- 1. 初始化本地数据库结构 ---
DB_PATH = "hao_harbour_db.csv"
STORAGE_DIR = "my_properties" # 所有海报存放在这里

if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

if not os.path.exists(DB_PATH):
    # 初始化数据库字段
    df = pd.DataFrame(columns=["date", "title", "region", "rooms", "price_month", "file_path"])
    df.to_csv(DB_PATH, index=False)

# --- 2. 核心绘图与AI逻辑 (保持之前定型的物理防截断逻辑) ---
def load_font(size):
    font_paths = ["simhei.ttf", "msyh.ttc", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
    for path in font_paths:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except: continue
    return ImageFont.load_default()

def pixel_wrap(text, font, max_pixel_width):
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        if font.getlength(test_line) <= max_pixel_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
    lines.append(current_line)
    return lines

# ... (此处省略上一版中已完美的 call_ai_summary, draw_checkmark, add_deep_watermark, create_poster 函数逻辑) ...
# 请确保在实际运行的代码中包含这些函数

# --- 3. UI 界面 ---
st.title("🏡 Hao Harbour 房源管理系统 V1.0")

# 侧边栏：分类查看功能
st.sidebar.header("🔍 房源库筛选")
view_region = st.sidebar.multiselect("按区域", ["中伦敦", "东伦敦", "西伦敦", "南伦敦", "北伦敦"])
view_rooms = st.sidebar.multiselect("按房型", ["1房", "2房", "3房", "4房+"])
view_price = st.sidebar.slider("最高月租预算 (£)", 1000, 15000, 15000)

# 主界面分页
tab_new, tab_library = st.tabs(["✨ 生成并存档", "📚 我的房源库"])

with tab_new:
    st.header("录入新房源")
    
    # 分类标签选择
    c1, c2, c3 = st.columns(3)
    with c1:
        reg = st.selectbox("区域分区", ["中伦敦", "东伦敦", "西伦敦", "南伦敦", "北伦敦"])
    with c2:
        rm = st.selectbox("房型分区", ["1房", "2房", "3房", "4房+"])
    with c3:
        price = st.number_input("月租价格 (£/pcm)", min_value=0, value=3000, step=100)
        
    title_input = st.text_input("房源名称 (如: Lexington Gardens)")
    desc = st.text_area("粘贴房源 Description")
    files = st.file_uploader("上传图片 (前8张)", accept_multiple_files=True)

    if st.button("🚀 生成海报并保存到归类"):
        if desc and files and title_input:
            with st.spinner("排版中..."):
                # 1. 生成海报
                poster_data = create_poster(files[:8], call_ai_summary(desc))
                
                # 2. 物理保存文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"{reg}_{rm}_{price}_{timestamp}.png"
                full_path = os.path.join(STORAGE_DIR, file_name)
                
                with open(full_path, "wb") as f:
                    f.write(poster_data)
                
                # 3. 记录到数据库
                new_entry = {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "title": title_input,
                    "region": reg,
                    "rooms": rm,
                    "price_month": price,
                    "file_path": full_path
                }
                pd.DataFrame([new_entry]).to_csv(DB_PATH, mode='a', header=False, index=False)
                
                st.success(f"已存档至 {reg} 分区！")
                st.image(poster_data)

with tab_library:
    st.header("库中房源预览")
    df_db = pd.read_csv(DB_PATH)
    
    # 应用侧边栏筛选逻辑
    if view_region:
        df_db = df_db[df_db['region'].isin(view_region)]
    if view_rooms:
        df_db = df_db[df_db['rooms'].isin(view_rooms)]
    df_db = df_db[df_db['price_month'] <= view_price]
    
    if df_db.empty:
        st.warning("没有找到匹配的房源。")
    else:
        # 网格展示
        cols = st.columns(3)
        for idx, row in df_db.iterrows():
            with cols[idx % 3]:
                st.markdown(f"### {row['title']}")
                st.markdown(f"**{row['region']} | {row['rooms']} | £{row['price_month']}**")
                if os.path.exists(row['file_path']):
                    st.image(row['file_path'])
                    with open(row['file_path'], "rb") as f:
                        st.download_button("下载此海报", f, file_name=os.path.basename(row['file_path']), key=f"dl_{idx}")
                st.divider()
