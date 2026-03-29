import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats
from scipy.interpolate import CubicSpline
import warnings
import hashlib, json, os, re, socket, base64, io
warnings.filterwarnings('ignore')

# ─── USER STORE (saved to users.json next to the script) ────────────────────
_USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")

def _load_users():
    if os.path.exists(_USERS_FILE):
        with open(_USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def _save_users(data):
    with open(_USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def _valid_email(e):
    return bool(re.match(r"^[\w.+\-]+@[\w\-]+\.[a-zA-Z]{2,}$", e.strip()))

def _valid_pw(pw):
    """Min 8 chars, at least one digit and one special character."""
    return (len(pw) >= 8
            and any(c.isdigit() for c in pw)
            and any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in pw))

# ─── QR CODE HELPER ──────────────────────────────────────────────────────────
def _get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def _qr_png_b64(url: str) -> str | None:
    """Return base64-encoded PNG of QR code, or None if qrcode not installed."""
    try:
        import qrcode
        from PIL import Image
        qr = qrcode.QRCode(version=2, box_size=6, border=3,
                           error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1a472a", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        return None

# ─── SESSION STATE ────────────────────────────────────────────────────────────
for _k, _v in [("authenticated", False), ("user_email", ""),
               ("user_name", ""), ("auth_tab", "login")]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MathVision – Nagaland Agriculture",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── AUTH CSS (only for login page) ──────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }
.auth-card {
    max-width: 420px; margin: 50px auto 0 auto;
    background: linear-gradient(160deg, #0d1f13 0%, #1a3a24 100%);
    border-radius: 20px; padding: 42px 38px;
    border: 1px solid rgba(82,183,136,0.25);
    box-shadow: 0 20px 60px rgba(0,0,0,0.45);
}
.auth-logo  { text-align:center; font-size:3rem; margin-bottom:4px; }
.auth-title {
    text-align:center; font-size:1.55rem; font-weight:700;
    background:linear-gradient(135deg,#52b788,#95d5b2);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    margin-bottom:2px;
}
.auth-sub   { text-align:center; color:#74b89a; font-size:0.84rem; margin-bottom:24px; }
.pw-rules   {
    background:rgba(255,255,255,0.05); border-radius:8px;
    padding:10px 14px; font-size:0.8rem; color:#95d5b2; margin-top:6px;
    border:1px solid rgba(82,183,136,0.2);
}
</style>
""", unsafe_allow_html=True)

# ─── AUTH SCREEN ─────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    _L, _M, _R = st.columns([1, 2.2, 1])
    with _M:
        st.markdown("""
        <div class="auth-card">
            <div class="auth-logo">🌾</div>
            <div class="auth-title">MathVision</div>
            <div class="auth-sub">Nagaland Agriculture Analytics · Secure Access</div>
        </div>
        """, unsafe_allow_html=True)

        _tab_login, _tab_signup = st.tabs(["🔐  Sign In", "📝  Create Account"])

        # ── SIGN IN ───────────────────────────────────────────────────────────
        with _tab_login:
            with st.form("form_login", clear_on_submit=False):
                _em = st.text_input("📧 Email", placeholder="you@example.com")
                _pw = st.text_input("🔑 Password", type="password", placeholder="Your password")
                _sub = st.form_submit_button("Sign In →", use_container_width=True, type="primary")
            if _sub:
                if not _em or not _pw:
                    st.error("Please fill in both fields.")
                else:
                    _users = _load_users()
                    _key = _em.strip().lower()
                    if _key not in _users:
                        st.error("No account found for that email. Please create one.")
                    elif _users[_key]["password_hash"] != _hash(_pw):
                        st.error("Incorrect password. Please try again.")
                    else:
                        st.session_state.authenticated = True
                        st.session_state.user_email    = _key
                        st.session_state.user_name     = _users[_key].get("name", _key)
                        st.rerun()

        # ── SIGN UP ───────────────────────────────────────────────────────────
        with _tab_signup:
            with st.form("form_signup", clear_on_submit=True):
                _sname = st.text_input("👤 Your Name",        placeholder="e.g. Ato Jamir")
                _sem   = st.text_input("📧 Email Address",    placeholder="you@example.com")
                _spw   = st.text_input("🔑 Create Password",  type="password",
                                        placeholder="Min 8 chars · 1 number · 1 special char")
                _spw2  = st.text_input("🔑 Confirm Password", type="password",
                                        placeholder="Repeat your password")
                st.markdown("""<div class="pw-rules">
                    Password rules: &nbsp;✔ at least 8 characters &nbsp;✔ one digit (0-9)
                    &nbsp;✔ one special character (!@#$%…)
                </div>""", unsafe_allow_html=True)
                _ssub = st.form_submit_button("Create Account →", use_container_width=True, type="primary")
            if _ssub:
                _users = _load_users()
                _ekey  = _sem.strip().lower()
                if not _sname.strip():
                    st.error("Please enter your name.")
                elif not _valid_email(_sem):
                    st.error("Please enter a valid email address.")
                elif _ekey in _users:
                    st.error("An account with that email already exists. Please sign in.")
                elif not _valid_pw(_spw):
                    st.error("Password must be at least 8 characters with at least one digit and one special character.")
                elif _spw != _spw2:
                    st.error("Passwords do not match.")
                else:
                    _users[_ekey] = {"name": _sname.strip(), "password_hash": _hash(_spw)}
                    _save_users(_users)
                    st.success(f"✅ Account created for {_sname.strip()}! Please switch to Sign In.")
    st.stop()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
* { font-family: 'Inter', sans-serif; }

/* ── Hide Streamlit branding ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

.main-title {
    background: linear-gradient(135deg,#1a472a,#2d6a4f,#52b788);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-size: 2.6rem; font-weight: 700; text-align: center; margin-bottom: 0;
}
.subtitle { text-align:center; color:#6c757d; font-size:1rem; margin-bottom:1.5rem; }
.math-box {
    background:linear-gradient(135deg,#eaf4fb,#d6eaf8); border-radius:12px;
    padding:16px 20px; border-left:4px solid #2874a6; margin:10px 0;
}
.math-box h4 { color:#1a5276; margin:0 0 8px 0; }
.math-box p  { color:#1f618d; margin:0; font-size:0.9rem; line-height:1.6; }
.story-box {
    background:linear-gradient(135deg,#fef9e7,#fdebd0); border-radius:12px;
    padding:16px 20px; border-left:4px solid #d68910; margin:10px 0;
}
.story-box h4 { color:#7d6608; margin:0 0 8px 0; }
.story-box p  { color:#6e2f0d; margin:0; font-size:0.9rem; line-height:1.6; }
.section-header {
    font-size:1.25rem; font-weight:700; color:#1a472a;
    border-bottom:2px solid #52b788; padding-bottom:6px; margin:22px 0 12px 0;
}
code { background:#eaf0f6; padding:2px 6px; border-radius:4px; font-size:0.85rem; }
</style>
""", unsafe_allow_html=True)

# ─── YEAR MAPPING ────────────────────────────────────────────────────────────────
# Agricultural year mapped to index:
# 2016→0, 2017→1, 2018→2, 2019→3, 2020→4,
# 2021→5, 2022→6, 2023→7, 2024→8, 2025→9
# Forecast: 2026→10, 2027→11, 2028→12
DISCRETE_YEARS = list(range(0, 10))        # 0,1,2,...,9
YEAR_TO_CAL    = {i: 2016+i for i in range(10)}   # index → calendar year
CAL_TO_YEAR    = {v: k for k, v in YEAR_TO_CAL.items()}
AG_LABELS      = [
    "2015-16","2016-17","2017-18","2018-19","2019-20",
    "2020-21","2021-22*","2022-23","2023-24","2024-25"
]
INTERP_YEAR    = 6   # 2021-22 → index 6 (calendar 2022)

# ─── FULL DATASET (all 10 years, all districts) ──────────────────────────────────
CROP_DATA = {
    "Jhum Paddy": {
        "color": "#2d6a4f",
        "districts": ["Kohima","Phek","Mokokchung","Tuensang","Mon",
                      "Wokha","Zunheboto","Peren","Kiphire","Longleng"],
        "production": {
            # ordered 2016 → 2025 (i.e. ag-year ending that year)
            "Kohima":     [10330,10340,10290,10240,10221,10205,11072,11938,11927,11901],
            "Phek":       [ 3360, 3330, 3230, 3260, 3254, 3234, 4350, 4292, 4293, 4490],
            "Mokokchung": [18640,18670,18570,18550,18516,18500,20000,20438,20422,18174],
            "Tuensang":   [20110,20140,20040,19980,19944,19928,18979,18495,18476,21411],
            "Mon":        [31840,31910,31790,31700,31642,31626,33200,33215,33189,33099],
            "Wokha":      [20240,20220,20120,20060,20024,20000,19750,19765,19744,19709],
            "Zunheboto":  [18510,18480,18380,18370,18337,18321,18400,18420,18405,18355],
            "Peren":      [12820,12750,12650,12550,12527,12511, 7800, 7813, 7812, 7397],
            "Kiphire":    [17040,16940,16840,16810,16779,16763,14800,14768,14756,15112],
            "Longleng":   [11800,11620,11520,11520,11499,11491,10800,10832,10823,10796],
        }
    },
    "Potato": {
        "color": "#d4a017",
        "districts": ["Kohima","Phek","Mokokchung","Tuensang","Mon",
                      "Dimapur","Wokha","Zunheboto","Peren","Kiphire","Longleng"],
        "production": {
            "Kohima":     [16180,16420, 6420,16420,16468,16514,13879,10237,10508,10927],
            "Phek":       [13790,13930,13930,14020,14061,14100, 9800, 9525, 9805,10175],
            "Mokokchung": [ 7410, 7600, 7600, 7600, 7622, 7645, 4700, 4646, 4745, 4723],
            "Tuensang":   [ 9490, 9600, 9600, 9600, 9628, 9660, 9852,10210,10461,11058],
            "Mon":        [ 4880, 4990, 4990, 5010, 5025, 5039, 3820, 3762, 3862, 3894],
            "Dimapur":    [ 8010, 8310, 8310, 8410, 8435, 8459, 7752, 6970, 7176, 7356],
            "Wokha":      [ 5590, 5690, 5700, 5710, 5727, 5743, 4400, 4317, 4432, 4454],
            "Zunheboto":  [ 2310, 2400, 2400, 2400, 2407, 2414, 1850, 1819, 1847, 1881],
            "Peren":      [ 2050, 2190, 2210, 2210, 2216, 2224, 4600, 4474, 4613, 4781],
            "Kiphire":    [ 1580, 1700, 1800, 1800, 1805, 1810, 1370, 1354, 1390, 1390],
            "Longleng":   [ 1850, 2010, 2060, 2060, 2066, 2072, 1620, 1598, 1641, 1654],
        }
    },
    "Ginger": {
        "color": "#c0392b",
        "districts": ["Kohima","Phek","Mokokchung","Tuensang","Mon",
                      "Dimapur","Wokha","Zunheboto","Kiphire","Longleng"],
        "production": {
            "Kohima":     [4100,4210,4210,4210,4274,4274,4350,4212,4338,4440],
            "Phek":       [3280,3470,3490,3570,3624,3624,8200,7956,8328,9160],
            "Mokokchung": [2640,2810,2940,2940,2975,2975,1750,1545,1784,1988],
            "Tuensang":   [2920,3010,3110,3110,3157,3157,3150,3124,3105,3335],
            "Mon":        [3930,4030,4030,4030,4091,4091,5100,4537,5229,5533],
            "Dimapur":    [5290,5360,5360,5370,5461,5461,4566,3488,3664,4124],
            "Wokha":      [3010,3180,3300,3390,3441,3441,2850,2766,2864,3130],
            "Zunheboto":  [2550,2660,2740,2740,2782,2782,2650,2530,2614,2817],
            "Kiphire":    [1730,1830,1920,2010,2041,2041,1600,1416,1573,1776],
            "Longleng":   [1920,2010,2110,2110,2142,2142,2350,2117,2306,2583],
        }
    },
    "Soyabean": {
        "color": "#8e44ad",
        "districts": ["Mon","Wokha","Peren","Kiphire"],
        "production": {
            "Mon":    [3840,3860,3860,3860,3876,4059,2800,2745,2799,2828],
            "Wokha":  [1840,1890,1940,1950,1958,2458,1550,1526,1566,1569],
            "Peren":  [1300,1320,1320,1350,1356,1524,1450,1421,1449,1451],
            "Kiphire":[1310,1330,1350,1390,1396,1738,1450,1421,1454,1466],
        }
    },
}

# ─── MATH HELPERS ───────────────────────────────────────────────────────────────
def linear_regression(x, y):
    x, y = np.array(x, float), np.array(y, float)
    slope, intercept, r, _, se = stats.linregress(x, y)
    r2 = r**2
    return slope, intercept, r2

def poly_regression(x, y, deg=2):
    x, y = np.array(x, float), np.array(y, float)
    coeffs = np.polyfit(x, y, deg)
    poly   = np.poly1d(coeffs)
    yp     = poly(x)
    ss_res = np.sum((y - yp)**2)
    ss_tot = np.sum((y - y.mean())**2)
    r2     = 1 - ss_res/ss_tot if ss_tot else 0
    return coeffs, poly, r2

def predict_future(years, production, n_future, model):
    x, y = np.array(years, float), np.array(production, float)
    fx   = np.array([x[-1] + i for i in range(1, n_future+1)])
    fl   = [f"{int(v)} ({2026 + int(v) - 10})" for v in fx]  # e.g. "10 (2026)"

    if model == "linear":
        s, b, r2 = linear_regression(x, y)
        fy = s*fx + b
        sx = np.linspace(x[0], fx[-1], 300)
        sy = s*sx + b
        eq = f"y = {s:.2f}·x + ({b:,.0f})"
    elif model == "polynomial":
        _, fn, r2 = poly_regression(x, y, 2)
        cs, _, _  = poly_regression(x, y, 2)
        fy = fn(fx)
        sx = np.linspace(x[0], fx[-1], 300)
        sy = fn(sx)
        eq = f"y = {cs[0]:.3f}·x² + {cs[1]:.1f}·x + {cs[2]:,.0f}"
    else:  # cubic spline
        cs_fn = CubicSpline(x, y)
        fy = cs_fn(fx)
        sx = np.linspace(x[0], fx[-1], 300)
        sy = cs_fn(sx)
        _, _, r2 = poly_regression(x, y, 3)
        eq = "Cubic Spline (piecewise)"
    return fy, fl, sx, sy, r2, eq

# ─── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌾 MathVision")
    st.markdown("**Nagaland Agriculture · 2016–2025**")
    st.markdown(f"👤 **{st.session_state.user_name}**")
    st.caption(st.session_state.user_email)
    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_email = ""
        st.session_state.user_name = ""
        st.rerun()
    st.markdown("---")

    crop_name = st.selectbox("🌱 Crop", list(CROP_DATA.keys()))
    crop      = CROP_DATA[crop_name]

    all_districts = crop["districts"]
    sel_districts = st.multiselect("📍 Districts", all_districts, default=all_districts[:3])
    if not sel_districts:
        sel_districts = all_districts[:1]

    model_choice = st.selectbox(
        "📐 Regression Model",
        ["linear","polynomial","cubic_spline"],
        format_func=lambda m: {"linear":"📏 Linear","polynomial":"📈 Polynomial (deg-2)","cubic_spline":"〰️ Cubic Spline"}[m]
    )
    n_pred = st.slider("🔮 Years to Predict Ahead", 1, 3, 2)
    show_residuals = st.checkbox("📉 Show Residuals Panel", value=False)
    show_table     = st.checkbox("📋 Show Full Data Table",  value=True)
    show_math      = st.checkbox("📐 Show Math Explanation", value=True)

    st.markdown("---")

    # ── QR Code & Share Link ──────────────────────────────────────
    # The QR must encode the REAL local IP so other devices can reach the app.
    # The branded name "MathVision 2026" is used only as a display label.
    _local_ip  = _get_local_ip()
    _real_url  = f"http://{_local_ip}:8501"   # actual address encoded in QR

    st.markdown("### 📲 Share MathVision 2026")

    # ── Link card — branded title, real IP shown below ────────────
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0d1f13,#1a3a24);
     border-radius:12px;padding:14px 16px;margin:4px 0 12px 0;
     border:1px solid rgba(82,183,136,0.4);">
  <div style="color:#74b89a;font-size:0.68rem;font-weight:600;
              letter-spacing:1.2px;margin-bottom:6px;">🌐 OPEN ON ANY DEVICE (same Wi-Fi)</div>
  <div style="color:#52b788;font-size:1.05rem;font-weight:800;
              margin-bottom:6px;">🌾 MathVision 2026</div>
  <div style="color:#95d5b2;font-size:0.78rem;font-family:monospace;
              word-break:break-all;font-weight:600;">{_real_url}</div>
  <div style="color:#74b89a;font-size:0.66rem;margin-top:6px;">
    📶 Device must be on the same Wi-Fi network as this computer</div>
</div>
""", unsafe_allow_html=True)

    # ── QR Code — encodes the real local IP URL ───────────────────
    import urllib.parse as _up
    _qr_size = "240x240"
    _qr_b64  = _qr_png_b64(_real_url)
    if _qr_b64:
        st.markdown(
            f"""<div style="text-align:center;padding:4px 0 8px 0;">
  <div style="font-size:0.7rem;color:#74b89a;font-weight:700;
              letter-spacing:1px;margin-bottom:8px;">📷 SCAN WITH PHONE CAMERA</div>
  <div style="display:inline-block;background:white;padding:10px;
              border-radius:14px;border:3px solid #52b788;
              box-shadow:0 6px 20px rgba(0,0,0,0.5);">
    <img src="data:image/png;base64,{_qr_b64}"
         width="200" style="display:block;border-radius:4px;"/>
  </div>
  <div style="font-size:0.7rem;color:#52b788;font-weight:700;margin-top:8px;">
    🌾 MathVision 2026</div>
  <div style="font-size:0.65rem;color:#6c9e82;margin-top:2px;">
    Opens at {_real_url}</div>
</div>""",
            unsafe_allow_html=True
        )
    else:
        _qr_encoded = _up.quote(_real_url, safe="")
        _qr_api = (f"https://api.qrserver.com/v1/create-qr-code/"
                   f"?size={_qr_size}&data={_qr_encoded}"
                   f"&color=1a3a24&bgcolor=ffffff&margin=12&qzone=2")
        st.markdown(
            f"""<div style="text-align:center;padding:4px 0 8px 0;">
  <div style="font-size:0.7rem;color:#74b89a;font-weight:700;
              letter-spacing:1px;margin-bottom:8px;">📷 SCAN WITH PHONE CAMERA</div>
  <div style="display:inline-block;background:white;padding:10px;
              border-radius:14px;border:3px solid #52b788;
              box-shadow:0 6px 20px rgba(0,0,0,0.5);">
    <img src="{_qr_api}" width="200"
         style="display:block;border-radius:4px;" alt="QR — MathVision 2026"/>
  </div>
  <div style="font-size:0.7rem;color:#52b788;font-weight:700;margin-top:8px;">
    🌾 MathVision 2026</div>
  <div style="font-size:0.65rem;color:#6c9e82;margin-top:2px;">
    Opens at {_real_url} · install <code>qrcode[pil]</code> for offline QR</div>
</div>""",
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.caption("★ Index 6 (2022) value estimated via interpolation (no official data).")
    st.caption("X-axis: index 0=2016, 1=2017 … 9=2025 | Forecast: 10=2026, 11=2027, 12=2028.")

# ─── HEADER ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🌾 MathVision — Nagaland Agriculture</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Full Historical Data 2016–2025 · Linear Regression · Forecasting · District Analysis</div>', unsafe_allow_html=True)

# ── Year-Index Highlight Banner ──────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#1a472a,#2d6a4f);border-radius:12px;
     padding:14px 20px;margin:8px 0 18px 0;color:white;font-size:0.88rem;line-height:2;">
<b>📅 Year Index Mapping</b><br>
<span style="background:#2ecc71;color:#000;border-radius:5px;padding:2px 7px;margin:2px;">0 = 2016</span>
<span style="background:#2ecc71;color:#000;border-radius:5px;padding:2px 7px;margin:2px;">1 = 2017</span>
<span style="background:#2ecc71;color:#000;border-radius:5px;padding:2px 7px;margin:2px;">2 = 2018</span>
<span style="background:#2ecc71;color:#000;border-radius:5px;padding:2px 7px;margin:2px;">3 = 2019</span>
<span style="background:#2ecc71;color:#000;border-radius:5px;padding:2px 7px;margin:2px;">4 = 2020</span>
<span style="background:#2ecc71;color:#000;border-radius:5px;padding:2px 7px;margin:2px;">5 = 2021</span>
<span style="background:#f39c12;color:#000;border-radius:5px;padding:2px 7px;margin:2px;">6 = 2022 ★</span>
<span style="background:#2ecc71;color:#000;border-radius:5px;padding:2px 7px;margin:2px;">7 = 2023</span>
<span style="background:#2ecc71;color:#000;border-radius:5px;padding:2px 7px;margin:2px;">8 = 2024</span>
<span style="background:#2ecc71;color:#000;border-radius:5px;padding:2px 7px;margin:2px;">9 = 2025</span>
&nbsp;&nbsp;
<span style="background:#e74c3c;color:#fff;border-radius:5px;padding:2px 7px;margin:2px;">🔮 10 = 2026</span>
<span style="background:#e74c3c;color:#fff;border-radius:5px;padding:2px 7px;margin:2px;">🔮 11 = 2027</span>
<span style="background:#e74c3c;color:#fff;border-radius:5px;padding:2px 7px;margin:2px;">🔮 12 = 2028</span>
&nbsp;&nbsp;<span style="font-size:0.78rem;opacity:0.8;">★ index 6 (2022) = interpolated</span>
</div>
""", unsafe_allow_html=True)

x_all    = DISCRETE_YEARS                      # [0,1,2,...,9]
# Labels: "0 (2016)", "1 (2017)", ..., "9 (2025)"
x_labels = [f"{i} ({2016+i})" for i in x_all]

# ─── TOP METRICS ────────────────────────────────────────────────────────────────
cols = st.columns(min(len(sel_districts), 4))
for col, dist in zip(cols, sel_districts[:4]):
    prod    = crop["production"][dist]
    latest  = prod[-1]
    delta   = latest - prod[-2]
    col.metric(f"🏔 {dist}", f"{latest:,.0f} MT", f"{delta:+,.0f} vs 2024")

st.markdown("---")

# ─── MAIN TREND CHART ───────────────────────────────────────────────────────────
st.markdown(f'<div class="section-header">📊 {crop_name} — Production vs Year (Discrete: 2016–2025)</div>', unsafe_allow_html=True)

palette = px.colors.qualitative.Bold
fig_main = go.Figure()

for i, dist in enumerate(sel_districts):
    prod = crop["production"][dist]
    col  = palette[i % len(palette)]
    fy, fl, sx, sy, r2, eq = predict_future(x_all, prod, n_pred, model_choice)

    # ── historical actual data ──
    marker_colors = ['gold' if yr == INTERP_YEAR else col for yr in x_all]
    marker_syms   = ['diamond' if yr == INTERP_YEAR else 'circle' for yr in x_all]

    fig_main.add_trace(go.Scatter(
        x=x_labels, y=prod, mode='lines+markers',
        name=f"{dist} (actual)",
        line=dict(color=col, width=2.5),
        marker=dict(size=[12 if yr == INTERP_YEAR else 7 for yr in x_all],
                    color=marker_colors, symbol=marker_syms,
                    line=dict(color=col, width=1.5)),
        hovertemplate=f"<b>{dist}</b><br>Year: %{{x}}<br>Production: %{{y:,.0f}} MT<extra></extra>"
    ))

    # ── regression / spline smooth line over historical range ──
    sx_hist = np.linspace(x_all[0], x_all[-1], 300)
    if model_choice == "linear":
        s, b, _ = linear_regression(x_all, prod)
        sy_hist = s * sx_hist + b
    elif model_choice == "polynomial":
        _, fn, _ = poly_regression(x_all, prod, 2)
        sy_hist  = fn(sx_hist)
    else:
        cs_fn   = CubicSpline(x_all, prod)
        sy_hist = cs_fn(sx_hist)

    fig_main.add_trace(go.Scatter(
        x=[f"{int(v)} ({int(2016+v)})" for v in sx_hist], y=sy_hist,
        mode='lines', name=f"{dist} (fit)",
        line=dict(color=col, width=1.5, dash='dot'),
        hoverinfo='skip', showlegend=False
    ))

    # ── forecast points ──
    fig_main.add_trace(go.Scatter(
        x=fl, y=fy, mode='markers+lines',
        name=f"{dist} ⭐ forecast",
        line=dict(color=col, width=2, dash='dash'),
        marker=dict(size=11, symbol='star', color='white',
                    line=dict(color=col, width=2.5)),
        hovertemplate=f"<b>{dist} FORECAST</b><br>Year Index: %{{x}}<br>Est.: %{{y:,.0f}} MT<extra></extra>"
    ))

# shade the forecast zone — use index-based labels
last_hist_x = f"{x_all[-1]} ({2016+x_all[-1]})"
forecast_tickvals = [f"{x_all[-1]+i} ({2016+x_all[-1]+i})" for i in range(1, n_pred+1)]
fig_main.add_vrect(
    x0=last_hist_x,
    x1=forecast_tickvals[-1],
    fillcolor="rgba(173,216,230,0.12)",
    line=dict(color="steelblue", dash="dash", width=1.5),
    annotation_text="◀ Forecast →", annotation_position="top left"
)

all_tickvals = x_labels + forecast_tickvals

fig_main.update_layout(
    title=dict(text=f"<b>{crop_name} Production (MT) — Index 0–9 (2016–2025) + Forecast 10–12 (2026–2028)</b>", font=dict(size=15)),
    xaxis=dict(
        title="Year Index (0=2016 … 9=2025 | 🔮 10=2026, 11=2027, 12=2028)",
        tickmode='array',
        tickvals=all_tickvals,
        ticktext=all_tickvals,
        tickangle=-30, gridcolor='#f0f0f0'
    ),
    yaxis=dict(title="Production (MT)", gridcolor='#f0f0f0',
               tickformat=','),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=500,
    plot_bgcolor="rgba(250,250,250,0.9)",
    paper_bgcolor="white",
    hovermode="x unified"
)
st.plotly_chart(fig_main, use_container_width=True)

st.caption("💎 Gold diamond = 2022 (interpolated for 2021-22 ag-year) | ⭐ Stars = Forecast | Dotted line = Regression fit")

# ─── PER-DISTRICT LINEAR REGRESSION CHARTS ──────────────────────────────────────
st.markdown(f'<div class="section-header">📈 Linear Regression — Production vs Year (per District)</div>', unsafe_allow_html=True)

st.markdown("""
<div class="story-box">
<h4>📖 What is Linear Regression?</h4>
<p>We draw the <b>best-fit straight line</b> through all 10 years of data.
The equation <code>y = m·x + c</code> tells us:<br>
• <b>m (slope)</b> → by how many MT production increases (or decreases) each year<br>
• <b>c (intercept)</b> → baseline value<br>
• <b>R²</b> → how well the line fits (1.0 = perfect, 0 = no fit)<br>
Each scatter point is one year; the line is what mathematics says the trend looks like.</p>
</div>
""", unsafe_allow_html=True)

# Display 2 columns of charts
n_cols = 2
district_chunks = [sel_districts[i:i+n_cols] for i in range(0, len(sel_districts), n_cols)]

for chunk in district_chunks:
    cols_lr = st.columns(n_cols)
    for col_lr, dist in zip(cols_lr, chunk):
        prod = np.array(crop["production"][dist], float)
        x_np = np.array(x_all, float)
        slope, intercept, r2 = linear_regression(x_np, prod)
        y_line = slope * x_np + intercept
        pred_next = slope * (x_all[-1] + 1) + intercept

        fig_lr = go.Figure()

        # scatter: actual
        fig_lr.add_trace(go.Scatter(
            x=x_labels, y=prod, mode='markers',
            marker=dict(
                size=[14 if yr == INTERP_YEAR else 9 for yr in x_all],
                color=['gold' if yr == INTERP_YEAR else crop["color"] for yr in x_all],
                symbol=['diamond' if yr == INTERP_YEAR else 'circle' for yr in x_all],
                line=dict(color='white', width=1)
            ),
            name="Actual", showlegend=False,
            hovertemplate="Year: %{x}<br>Production: %{y:,.0f} MT<extra></extra>"
        ))

        # regression line extended slightly into future
        x_ext = np.array([x_all[0], x_all[-1] + 1], float)
        y_ext = slope * x_ext + intercept
        fig_lr.add_trace(go.Scatter(
            x=[f"{int(v)} ({int(2016+v)})" for v in x_ext], y=y_ext,
            mode='lines', name="Linear fit", showlegend=False,
            line=dict(color=crop["color"], width=2.5)
        ))

        # residual lines (vertical)
        for xi, yi, yfi in zip(x_labels, prod, y_line):
            fig_lr.add_shape(type='line',
                x0=xi, x1=xi, y0=yi, y1=yfi,
                line=dict(color='rgba(200,0,0,0.35)', width=1.5, dash='dot')
            )

        # annotation for slope & R²
        trend_txt = f"▲ +{slope:.0f}/yr" if slope >= 0 else f"▼ {slope:.0f}/yr"
        fig_lr.add_annotation(
            x=0.03, y=0.97, xref='paper', yref='paper', showarrow=False,
            text=f"<b>y = {slope:.1f}x + {intercept:,.0f}</b><br>R² = {r2:.4f}<br>{trend_txt}",
            align='left', bgcolor='rgba(255,255,255,0.85)',
            bordercolor=crop["color"], borderwidth=1,
            font=dict(size=10, color=crop["color"])
        )

        fig_lr.update_layout(
            title=dict(text=f"<b>{dist}</b>", font=dict(size=13, color=crop["color"])),
            xaxis=dict(
                title="Year Index (0=2016 … 9=2025)",
                tickmode='array',
                tickvals=x_labels, ticktext=x_labels,
                tickangle=-45, gridcolor='#f5f5f5'
            ),
            yaxis=dict(title="Production (MT)", gridcolor='#f5f5f5', tickformat=','),
            height=310,
            margin=dict(l=50, r=20, t=40, b=55),
            plot_bgcolor='rgba(248,249,250,0.9)',
            paper_bgcolor='white'
        )
        col_lr.plotly_chart(fig_lr, use_container_width=True)

# ─── REGRESSION SUMMARY TABLE ───────────────────────────────────────────────────
st.markdown(f'<div class="section-header">📋 Linear Regression Summary — All Districts ({crop_name})</div>', unsafe_allow_html=True)

rows = []
for dist in crop["districts"]:
    prod = crop["production"][dist]
    s, b, r2 = linear_regression(x_all, prod)
    pred_26 = s * (x_all[-1]+1) + b
    pred_27 = s * (x_all[-1]+2) + b
    rows.append({
        "District":            dist,
        "Slope (MT/idx)":      f"{s:+.1f}",
        "Intercept":           f"{b:,.0f}",
        "R²":                  f"{r2:.4f}",
        "Fit Quality":         "✅ Excellent" if r2>0.8 else ("🟡 Moderate" if r2>0.5 else "🔴 Low"),
        "Trend":               f"{'📈' if s>0 else '📉'} {abs(s):.0f} MT/idx",
        "🔮 Idx 10 (2026) MT": f"{pred_26:,.0f}",
        "🔮 Idx 11 (2027) MT": f"{pred_27:,.0f}",
    })

df_summary = pd.DataFrame(rows)
st.dataframe(df_summary, hide_index=True, use_container_width=True)

# ─── RESIDUALS ──────────────────────────────────────────────────────────────────
if show_residuals and sel_districts:
    st.markdown(f'<div class="section-header">📉 Residual Analysis</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="math-box">
<h4>What is a Residual?</h4>
<p><code>Residual = Actual − Predicted</code><br>
If residuals are close to zero and random, the model is good.
A pattern in residuals means there's something the line isn't capturing (e.g. a curve or cycle).</p>
</div>
""", unsafe_allow_html=True)

    cols_res = st.columns(min(len(sel_districts), 3))
    for col_r, dist in zip(cols_res, sel_districts[:3]):
        prod = np.array(crop["production"][dist], float)
        s, b, r2 = linear_regression(x_all, prod)
        residuals = prod - (s * np.array(x_all, float) + b)
        fig_res = go.Figure()
        fig_res.add_hline(y=0, line=dict(color='black', width=1))
        fig_res.add_trace(go.Bar(
            x=x_labels, y=residuals,
            marker_color=['#e74c3c' if r < 0 else '#2ecc71' for r in residuals],
            name="Residual"
        ))
        fig_res.update_layout(
            title=f"Residuals — {dist}",
            xaxis=dict(tickvals=x_labels, ticktext=x_labels, tickangle=-45),
            yaxis_title="Residual (MT)",
            height=260, plot_bgcolor='rgba(248,249,250,0.9)',
            showlegend=False
        )
        col_r.plotly_chart(fig_res, use_container_width=True)

# ─── MATH EXPLANATION ───────────────────────────────────────────────────────────
if show_math:
    st.markdown(f'<div class="section-header">📐 Mathematics — Step by Step</div>', unsafe_allow_html=True)
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("""
<div class="math-box">
<h4>📅 Year Index Encoding</h4>
<p>
Agricultural years are mapped to simple indices starting at 0:<br>
<code>2015-16 → 0 &nbsp;|&nbsp; 2016-17 → 1 &nbsp;|&nbsp; … &nbsp;|&nbsp; 2024-25 → 9</code><br><br>
Forecast years continue the sequence:<br>
<code>2025-26 → 10 &nbsp;|&nbsp; 2026-27 → 11 &nbsp;|&nbsp; 2027-28 → 12</code><br><br>
This gives a clean zero-based X-axis: <b>0, 1, 2, …, 9</b> (historical) and <b>10, 11, 12</b> (forecast).
</p>
</div>
""", unsafe_allow_html=True)
        st.markdown("""
<div class="math-box">
<h4>📏 Linear Regression Formula</h4>
<p>
We minimise: <code>Σ(yᵢ − (m·xᵢ + c))²</code><br><br>
Closed-form solution:<br>
<code>m = [n·Σxᵢyᵢ − Σxᵢ·Σyᵢ] / [n·Σxᵢ² − (Σxᵢ)²]</code><br>
<code>c = (Σyᵢ − m·Σxᵢ) / n</code><br><br>
<b>R²</b> = 1 − SS_res/SS_tot &nbsp; (0 to 1; higher = better fit)
</p>
</div>
""", unsafe_allow_html=True)
    with col_m2:
        st.markdown("""
<div class="math-box">
<h4>🔶 Interpolation (2021-22 Missing Year → Index 6)</h4>
<p>
Official data for 2021-22 was unavailable.<br>
Linear interpolation between index 5 (2021) and index 7 (2023):<br>
<code>f(6) = [f(5) + f(7)] / 2</code><br><br>
For cubic spline, we fit a smooth curve through all known indices and read off index 6.
The interpolated points are marked with <b>gold diamonds</b> on every chart.
</p>
</div>
""", unsafe_allow_html=True)
        st.markdown("""
<div class="math-box">
<h4>🔮 Prediction (Beyond Index 9 / 2025)</h4>
<p>
Once we have the regression equation <code>y = m·x + c</code>, prediction is trivial:<br>
<code>ŷ(10) = m × 10 + c &nbsp;→ 2026</code><br>
<code>ŷ(11) = m × 11 + c &nbsp;→ 2027</code><br>
<code>ŷ(12) = m × 12 + c &nbsp;→ 2028</code><br><br>
For polynomial/spline, the same principle holds — plug in the future index into the fitted function.
</p>
</div>
""", unsafe_allow_html=True)

# ─── FULL DATA TABLE ────────────────────────────────────────────────────────────
if show_table:
    st.markdown(f'<div class="section-header">📋 Full Data Table — {crop_name} (Index 0–9 → 2016–2025)</div>', unsafe_allow_html=True)
    table_dict = {"Index (Year)": x_labels, "Ag. Season": AG_LABELS}
    for dist in sel_districts:
        table_dict[dist] = [
            f"{v:,.0f} {'★' if yr == INTERP_YEAR else ''}"
            for v, yr in zip(crop["production"][dist], x_all)
        ]
    df_table = pd.DataFrame(table_dict)
    st.dataframe(df_table.set_index("Index (Year)"), use_container_width=True)
    st.caption("★ = interpolated value (index 6 / 2022, no official data for 2021-22 agricultural year)")

# ─── LIVE DEMO ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header">🎮 Live Demo — Enter 10-Year Values & Predict 3 Years Ahead</div>', unsafe_allow_html=True)

st.markdown("""
<div class="story-box">
<h4>🎯 On-the-spot prediction — full 10-year input!</h4>
<p>Enter production values for <b>all 10 years</b> (indices 0–9, ag-seasons 2015-16 to 2024-25).
The regression model trains on all 10 data points and predicts the next <b>3 years</b> (2026, 2027, 2028).
Same math, any numbers — try editing them to see the predictions update instantly.</p>
</div>
""", unsafe_allow_html=True)

# ── Model selector ────────────────────────────────────────────────────────────
_dc1, _dc2 = st.columns([3, 1])
with _dc1:
    demo_model = st.selectbox("📐 Prediction Model", ["linear", "polynomial"], key="dm",
        format_func=lambda x: "📏 Linear" if x == "linear" else "📈 Polynomial (deg-2)")
with _dc2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Reset", key="demo_reset", use_container_width=True):
        for _ri in range(10):
            _default = [15000,15500,16200,15800,16500,17100,16800,14500,15200,15800][_ri]
            st.session_state[f"d{_ri}"] = float(_default)

# ── 10 inputs in 2 rows of 5 ─────────────────────────────────────────────────
_DEMO_DEFAULTS = [15000,15500,16200,15800,16500,17100,16800,14500,15200,15800]
_DEMO_AG = ["2015-16","2016-17","2017-18","2018-19","2019-20",
            "2020-21","2021-22★","2022-23","2023-24","2024-25"]

st.markdown("**📥 Enter production (MT) for each of the 10 agricultural years:**")
dv = []
for _row in range(2):
    _rcols = st.columns(5)
    for _ci in range(5):
        _idx = _row * 5 + _ci
        _val = _rcols[_ci].number_input(
            f"{_idx} · {_DEMO_AG[_idx]}",
            value=float(_DEMO_DEFAULTS[_idx]),
            step=100.0, min_value=0.0, key=f"d{_idx}",
            help=f"Production in MT for index {_idx} ({_DEMO_AG[_idx]})"
        )
        dv.append(_val)

demo_x = list(range(10))   # indices 0–9
demo_y = dv

# ── Compute regression + 3-year forecast ─────────────────────────────────────
_fx = np.array([10, 11, 12])
_fy_labels = ["10 (2026)", "11 (2027)", "12 (2028)"]

if demo_model == "linear":
    s, b, r2 = linear_regression(demo_x, demo_y)
    _fy = s * _fx + b
    _sx_d = np.linspace(0, 12, 300)
    _sy_d = s * _sx_d + b
    eq_str = f"y = {s:.2f}·x + {b:,.0f}"
else:
    cs_d, fn_d, r2 = poly_regression(demo_x, demo_y, 2)
    _fy = fn_d(_fx)
    _sx_d = np.linspace(0, 12, 300)
    _sy_d = fn_d(_sx_d)
    eq_str = f"y = {cs_d[0]:.3f}·x² + {cs_d[1]:.1f}·x + {cs_d[2]:,.0f}"

# ── Metrics row ───────────────────────────────────────────────────────────────
mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("📐 Model", demo_model.title())
mc2.metric("R² Accuracy", f"{r2:.4f}")
mc3.metric("🔮 2026 (idx 10)", f"{_fy[0]:,.0f} MT", delta=f"{_fy[0]-demo_y[-1]:+,.0f}")
mc4.metric("🔮 2027 (idx 11)", f"{_fy[1]:,.0f} MT", delta=f"{_fy[1]-_fy[0]:+,.0f}")
mc5.metric("🔮 2028 (idx 12)", f"{_fy[2]:,.0f} MT", delta=f"{_fy[2]-_fy[1]:+,.0f}")

# ── Chart — all traces use NUMERIC x (0-12) for clean uniform scaling ───────
fig_demo = go.Figure()

# Tick mapping: integer index → readable label
_tick_vals = list(range(13))   # 0..12
_tick_text = [f"{i}\n({2016+i})" if i <= 9 else f"{i}\n({2016+i}) 🔮" for i in range(13)]

# Historical actual points (numeric x = 0..9)
_mk_color = ['gold' if i == INTERP_YEAR else '#2d6a4f' for i in range(10)]
_mk_sym   = ['diamond' if i == INTERP_YEAR else 'circle' for i in range(10)]
_mk_sz    = [13 if i == INTERP_YEAR else 9 for i in range(10)]
_hover_lbl = [f"Index {i} ({2016+i})<br>{_DEMO_AG[i]}" for i in range(10)]
fig_demo.add_trace(go.Scatter(
    x=list(range(10)), y=demo_y, mode='lines+markers',
    marker=dict(size=_mk_sz, color=_mk_color, symbol=_mk_sym,
                line=dict(color='#2d6a4f', width=1.5)),
    line=dict(color='#2d6a4f', width=2.5), name="Your data (10 yrs)",
    customdata=_hover_lbl,
    hovertemplate="%{customdata}<br>Production: %{y:,.0f} MT<extra></extra>"
))

# Regression smooth line — numeric x 0→9
_sx_hist = np.linspace(0, 9, 200)
_sy_hist = (s * _sx_hist + b) if demo_model == "linear" else fn_d(_sx_hist)
fig_demo.add_trace(go.Scatter(
    x=_sx_hist, y=_sy_hist, mode='lines',
    line=dict(color='#e67e22', dash='dot', width=2),
    name="Regression fit", hoverinfo='skip'
))

# Forecast smooth extension — numeric x 9→12
_sx_fore = np.linspace(9, 12, 80)
_sy_fore = (s * _sx_fore + b) if demo_model == "linear" else fn_d(_sx_fore)
fig_demo.add_trace(go.Scatter(
    x=_sx_fore, y=_sy_fore, mode='lines',
    line=dict(color='#e67e22', dash='dash', width=2),
    name="Forecast extension", hoverinfo='skip'
))

# Forecast star markers at x = 10, 11, 12
fig_demo.add_trace(go.Scatter(
    x=[10, 11, 12], y=_fy, mode='markers+text',
    marker=dict(size=16, symbol='star', color='#e74c3c',
                line=dict(color='white', width=1.5)),
    text=[f"{v:,.0f}" for v in _fy], textposition="top center",
    textfont=dict(size=11, color='#c0392b'),
    name="🔮 Forecast",
    hovertemplate="<b>FORECAST %{x}</b><br>Predicted: %{y:,.0f} MT<extra></extra>"
))

# Vertical divider + shaded forecast zone
fig_demo.add_shape(type="rect", x0=9.5, x1=12.4, y0=0, y1=1,
    xref="x", yref="paper",
    fillcolor="rgba(231,76,60,0.05)",
    line=dict(color="rgba(231,76,60,0.25)", width=1, dash="dot"))
fig_demo.add_shape(type="line", x0=9.5, x1=9.5, y0=0, y1=1,
    xref="x", yref="paper",
    line=dict(color="steelblue", width=1.8, dash="dash"))
fig_demo.add_annotation(x=9.5, y=1.05, xref="x", yref="paper",
    text="◀ Historical | Forecast ▶", showarrow=False,
    font=dict(color="steelblue", size=10))

# Y-axis: add a small top padding so text labels on stars don't clip
_y_min = min(min(demo_y), float(np.min(_fy))) * 0.97
_y_max = max(max(demo_y), float(np.max(_fy))) * 1.08

fig_demo.update_layout(
    height=420,
    plot_bgcolor='rgba(248,249,250,0.9)', paper_bgcolor='white',
    title=dict(
        text=f"<b>Live Regression & 3-Year Forecast</b> — {demo_model.title()} model | {eq_str}",
        font=dict(size=13)
    ),
    xaxis=dict(
        title="Year Index  (0 = 2015-16  …  9 = 2024-25  |  🔮 10-12 = Forecast)",
        tickmode='array',
        tickvals=_tick_vals,
        ticktext=_tick_text,
        tickangle=0,
        gridcolor='#ebebeb',
        range=[-0.5, 12.6],
        dtick=1,
    ),
    yaxis=dict(
        title="Production (MT)",
        gridcolor='#ebebeb',
        tickformat=',',
        range=[_y_min, _y_max],
        zeroline=False,
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hovermode="x unified",
    margin=dict(l=70, r=30, t=70, b=70),
)
st.plotly_chart(fig_demo, use_container_width=True)
st.caption("💎 Gold diamond = index 6 (2021-22, interpolated) | ⭐ Red stars = 3-year forecast | All 13 indices evenly spaced")

# ─── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#6c757d;font-size:0.82rem;'>
🌾 <b>MathVision</b> — Mathematics in Agriculture | Nagaland, India | Data: Nagaland Agriculture Dept. (2015-2025)<br>
X-axis index: 0=2016, 1=2017 … 9=2025 | Forecast: 10=2026, 11=2027, 12=2028 &nbsp;|&nbsp; ★ Index 6 (2022) = interpolated value
</div>
""", unsafe_allow_html=True)
