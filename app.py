import streamlit as st
import numpy as np
import cv2

from cartoonify import cartoonify_image

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="Cartoonify App",
    page_icon="🎨",
    layout="wide"
)

# -----------------------------
# Title
# -----------------------------
st.title("🎨 Cartoonify Image App")
st.write("Upload an image and convert it into a cartoon style!")

# -----------------------------
# File Upload
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload an image",
    type=["jpg", "jpeg", "png", "webp"]
)

# -----------------------------
# Sidebar Controls
# -----------------------------
st.sidebar.header("⚙️ Settings")

blur_type = st.sidebar.selectbox(
    "Blur Type",
    ["bilateral", "median", "gaussian"]
)

quantizer = st.sidebar.selectbox(
    "Quantization Method",
    ["kmeans", "mediancut"]
)

num_colors = st.sidebar.slider(
    "Number of Colors",
    min_value=4,
    max_value=32,
    value=8
)

line_strength = st.sidebar.slider(
    "Line Strength",
    min_value=0.1,
    max_value=2.0,
    value=0.5
)

target_long_side = st.sidebar.slider(
    "Image Resolution",
    min_value=256,
    max_value=2048,
    value=1024
)

upscale_small = st.sidebar.checkbox(
    "Upscale Small Images",
    value=True
)

# -----------------------------
# Processing
# -----------------------------
if uploaded_file is not None:
    # Convert uploaded file to OpenCV format
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if img is None:
        st.error("❌ Could not read the image")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Original Image")
            st.image(img, use_column_width=True)

        if st.button("✨ Cartoonify Image"):
            with st.spinner("Processing... please wait"):
                try:
                    result = cartoonify_image(
                        img,
                        blur_type=blur_type,
                        quantizer=quantizer,
                        num_colors=num_colors,
                        line_strength=line_strength,
                        target_long_side=target_long_side,
                        upscale_small=upscale_small,
                    )

                    with col2:
                        st.subheader("Cartoonified Image")
                        st.image(result, use_column_width=True)

                    # -----------------------------
                    # Download Button
                    # -----------------------------
                    _, buffer = cv2.imencode(".png", result)
                    st.download_button(
                        label="📥 Download Image",
                        data=buffer.tobytes(),
                        file_name="cartoonified.png",
                        mime="image/png"
                    )

                except Exception as e:
                    st.error(f"❌ Error: {e}")

else:
    st.info("👆 Upload an image to get started")
