import streamlit as st
import numpy as np
import cv2
from pathlib import Path
from PIL import Image
from cartoonify import cartoonify_image
from streamlit_image_comparison import image_comparison

st.set_page_config(page_title="Sketchify Web", page_icon="🎨", layout="wide")

st.markdown("""
<style>
/* Base overrides */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f0a1a 0%, #1a1035 25%, #1e1245 50%, #1a0a30 75%, #0f0a1a 100%);
    background-size: 400% 400%;
    animation: gradientShift 15s ease infinite;
}
[data-testid="stSidebar"] {
    background: rgba(30, 20, 50, 0.65);
    backdrop-filter: blur(16px);
    border-right: 1px solid rgba(139, 92, 246, 0.12);
}

/* Animations */
@keyframes gradientShift {
  0%   { background-position: 0% 50% }
  50%  { background-position: 100% 50% }
  100% { background-position: 0% 50% }
}
@keyframes orbFloat1 {
  0%, 100% { transform: translate(0, 0) scale(1) }
  33%      { transform: translate(40px, -30px) scale(1.1) }
  66%      { transform: translate(-20px, 20px) scale(.95) }
}
@keyframes orbFloat2 {
  0%, 100% { transform: translate(0, 0) scale(1) }
  33%      { transform: translate(-30px, 20px) scale(.9) }
  66%      { transform: translate(25px, -25px) scale(1.08) }
}

/* Hide default components */
header { visibility: hidden !important; }

/* Decorative Orbs */
.bg-orbs { position: fixed; inset: 0; pointer-events: none; z-index: -1; overflow: hidden; }
.bg-orbs .orb { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.35; }
.bg-orbs .orb:nth-child(1) {
  width: 500px; height: 500px;
  background: radial-gradient(circle, #6366f1, transparent 70%);
  top: -10%; left: -8%;
  animation: orbFloat1 18s ease-in-out infinite;
}
.bg-orbs .orb:nth-child(2) {
  width: 400px; height: 400px;
  background: radial-gradient(circle, #f5d0fe, transparent 70%);
  bottom: -5%; right: -5%;
  animation: orbFloat2 22s ease-in-out infinite;
}
.bg-orbs .orb:nth-child(3) {
  width: 300px; height: 300px;
  background: radial-gradient(circle, #c4b5fd, transparent 70%);
  top: 40%; left: 55%;
  animation: orbFloat1 20s ease-in-out infinite reverse;
}
</style>

<div class="bg-orbs" aria-hidden="true">
    <div class="orb"></div>
    <div class="orb"></div>
    <div class="orb"></div>
</div>
""", unsafe_allow_html=True)

st.title("🎨 Sketchify Web")
st.markdown("**AI Cartoonifier** - Transform your photos into vibrant cartoon-style artwork.", unsafe_allow_html=True)

st.sidebar.header("⚙️ Settings")

blur_type = st.sidebar.selectbox("Smoothing", ["bilateral", "median", "gaussian"], index=0)
quantizer = st.sidebar.selectbox("Quantizer", ["kmeans", "mediancut"], index=0)

num_colors = st.sidebar.slider("Colors", min_value=4, max_value=32, value=8)
line_strength = st.sidebar.slider("Edge Thickness", min_value=0.1, max_value=2.0, value=0.5, step=0.1)
target_long_side = st.sidebar.slider("Target Resolution", min_value=256, max_value=2048, value=1024, step=256)
upscale_small = st.sidebar.checkbox("Smart Upscale Small Images", value=True)

uploaded_file = st.file_uploader("Drop or browse JPG, PNG, WEBP (Limit 20MB)", type=["jpg", "jpeg", "png", "webp"])

if uploaded_file is not None:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if img is None:
        st.error("❌ Could not read the image")
    else:        
        if st.button("✦ Run Sketchify", use_container_width=True, type="primary"):
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

                    st.markdown("### Result Comparison")
                    # Convert BGR to RGB for Streamlit rendering
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    res_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
                    
                    image_comparison(
                        img1=Image.fromarray(img_rgb),
                        img2=Image.fromarray(res_rgb),
                        label1="Original",
                        label2="Cartoonified"
                    )

                    # Download button
                    _, buffer = cv2.imencode(".png", result)
                    st.download_button(
                        label="📥 Download High-Res PNG",
                        data=buffer.tobytes(),
                        file_name="cartoonified.png",
                        mime="image/png"
                    )
                except Exception as e:
                    st.error(f"❌ Error: {e}")
