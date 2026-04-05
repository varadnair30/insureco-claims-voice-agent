"""Generate a clean architecture diagram PNG for the Observe Insurance Claims Assistant."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Canvas
W, H = 2000, 1300
BG = (248, 250, 252)  # slate-50

# Brand colors (match the presentation deck)
TEAL = (8, 145, 178)       # primary
TEAL_LIGHT = (165, 243, 252)
NAVY = (30, 41, 59)         # text
NAVY_DARK = (15, 27, 45)
SLATE = (100, 116, 139)
WHITE = (255, 255, 255)
GREEN = (22, 163, 74)
AMBER = (234, 88, 12)
CARD_BORDER = (203, 213, 225)
SHADOW = (15, 23, 42, 40)

# Fonts
def load_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()

F_TITLE = load_font(52, bold=True)
F_SUBTITLE = load_font(26)
F_SECTION = load_font(22, bold=True)
F_BOX_TITLE = load_font(30, bold=True)
F_BOX_SUB = load_font(20)
F_BOX_DETAIL = load_font(18)
F_ARROW = load_font(18, bold=True)
F_CAPTION = load_font(16)
F_FOOTER = load_font(18)

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img, "RGBA")


def text_size(txt, font):
    bbox = draw.textbbox((0, 0), txt, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def rounded_card(x, y, w, h, fill=WHITE, border=CARD_BORDER, border_w=2, radius=18, shadow=True):
    if shadow:
        # subtle drop shadow
        for off in range(6, 0, -1):
            alpha = int(8 * off)
            draw.rounded_rectangle(
                [x + 3, y + 3 + off, x + w + 3, y + h + 3 + off],
                radius=radius, fill=(15, 23, 42, alpha)
            )
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=fill, outline=border, width=border_w)


def centered_text(cx, cy, txt, font, fill=NAVY):
    tw, th = text_size(txt, font)
    draw.text((cx - tw / 2, cy - th / 2), txt, font=font, fill=fill)


def left_text(x, y, txt, font, fill=NAVY):
    draw.text((x, y), txt, font=font, fill=fill)


def arrow(x1, y1, x2, y2, color=TEAL, width=4, label=None, label_above=True):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    # arrowhead
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_len = 18
    ax = x2 - arrow_len * math.cos(angle - math.pi / 7)
    ay = y2 - arrow_len * math.sin(angle - math.pi / 7)
    bx = x2 - arrow_len * math.cos(angle + math.pi / 7)
    by = y2 - arrow_len * math.sin(angle + math.pi / 7)
    draw.polygon([(x2, y2), (ax, ay), (bx, by)], fill=color)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        tw, th = text_size(label, F_ARROW)
        pad = 6
        box_x1, box_y1 = mx - tw / 2 - pad, my - th / 2 - pad
        box_x2, box_y2 = mx + tw / 2 + pad, my + th / 2 + pad
        draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=6, fill=WHITE, outline=color, width=2)
        draw.text((mx - tw / 2, my - th / 2), label, font=F_ARROW, fill=color)


# ═══════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════
draw.rectangle([0, 0, W, 120], fill=NAVY_DARK)
left_text(60, 28, "Observe Insurance Claims Assistant", F_TITLE, fill=WHITE)
left_text(62, 88, "Voice AI Agent  |  System Architecture", F_SUBTITLE, fill=(165, 243, 252))

# teal accent bar
draw.rectangle([0, 120, W, 128], fill=TEAL)

# ═══════════════════════════════════════════════════════════════
# LAYER 1 — CALLER
# ═══════════════════════════════════════════════════════════════
left_text(60, 160, "1. CALLER", F_SECTION, fill=SLATE)

caller_x, caller_y, caller_w, caller_h = 60, 200, 320, 160
rounded_card(caller_x, caller_y, caller_w, caller_h, fill=WHITE, border=TEAL, border_w=3)
centered_text(caller_x + caller_w / 2, caller_y + 50, "Customer", F_BOX_TITLE, fill=NAVY)
centered_text(caller_x + caller_w / 2, caller_y + 95, "Web Call / Phone", F_BOX_SUB, fill=SLATE)
centered_text(caller_x + caller_w / 2, caller_y + 125, "(VAPI Web SDK today)", F_BOX_DETAIL, fill=SLATE)

# ═══════════════════════════════════════════════════════════════
# LAYER 2 — VAPI ORCHESTRATION
# ═══════════════════════════════════════════════════════════════
left_text(480, 160, "2. VOICE ORCHESTRATION", F_SECTION, fill=SLATE)

vapi_x, vapi_y, vapi_w, vapi_h = 480, 200, 720, 440
rounded_card(vapi_x, vapi_y, vapi_w, vapi_h, fill=(240, 253, 255), border=TEAL, border_w=3)

# VAPI header strip
draw.rounded_rectangle([vapi_x, vapi_y, vapi_x + vapi_w, vapi_y + 64], radius=18, fill=TEAL)
draw.rectangle([vapi_x, vapi_y + 40, vapi_x + vapi_w, vapi_y + 64], fill=TEAL)
centered_text(vapi_x + vapi_w / 2, vapi_y + 32, "VAPI  —  Voice Orchestration Layer", F_BOX_TITLE, fill=WHITE)

# Three sub-components: STT, LLM, TTS
sub_w, sub_h = 210, 300
sub_y = vapi_y + 100
gap = 20
start_x = vapi_x + (vapi_w - (sub_w * 3 + gap * 2)) / 2

subs = [
    ("STT", "Deepgram", "Nova-2", "English-locked\nlow-latency\ntranscription", TEAL),
    ("LLM", "OpenAI", "GPT-4o", "Tool-use reasoning\nsystem prompt\nconversation mgmt", TEAL),
    ("TTS", "ElevenLabs", "Rachel voice", "Natural prosody\ncharacter-level\nsynthesis", TEAL),
]

for i, (label, vendor, model, detail, color) in enumerate(subs):
    sx = start_x + i * (sub_w + gap)
    rounded_card(sx, sub_y, sub_w, sub_h, fill=WHITE, border=color, border_w=2, shadow=False)
    # label chip
    draw.rounded_rectangle([sx + 20, sub_y + 20, sx + 90, sub_y + 56], radius=18, fill=TEAL)
    centered_text(sx + 55, sub_y + 38, label, F_ARROW, fill=WHITE)
    # vendor
    left_text(sx + 20, sub_y + 80, vendor, F_BOX_TITLE, fill=NAVY)
    # model
    left_text(sx + 20, sub_y + 120, model, F_BOX_SUB, fill=TEAL)
    # detail
    for j, line in enumerate(detail.split("\n")):
        left_text(sx + 20, sub_y + 170 + j * 28, "• " + line, F_BOX_DETAIL, fill=SLATE)

# ═══════════════════════════════════════════════════════════════
# LAYER 3 — FASTAPI BACKEND
# ═══════════════════════════════════════════════════════════════
left_text(1290, 160, "3. CUSTOM BACKEND", F_SECTION, fill=SLATE)

be_x, be_y, be_w, be_h = 1290, 200, 650, 440
rounded_card(be_x, be_y, be_w, be_h, fill=(254, 252, 232), border=AMBER, border_w=3)

draw.rounded_rectangle([be_x, be_y, be_x + be_w, be_y + 64], radius=18, fill=AMBER)
draw.rectangle([be_x, be_y + 40, be_x + be_w, be_y + 64], fill=AMBER)
centered_text(be_x + be_w / 2, be_y + 32, "FastAPI Backend  (Python)", F_BOX_TITLE, fill=WHITE)

# Inner modules
mod_x = be_x + 30
mod_y = be_y + 90
mod_w = be_w - 60
mod_h = 95
modules = [
    ("Webhook Dispatcher", "POST /webhook/vapi  →  routes tool-calls & end-of-call events"),
    ("Tool Handler", "lookup_caller()  →  Google Sheets customer lookup"),
    ("Summarizer", "GPT-4o-mini  →  structured JSON (summary + sentiment)"),
]
for i, (title, sub) in enumerate(modules):
    y = mod_y + i * (mod_h + 12)
    rounded_card(mod_x, y, mod_w, mod_h, fill=WHITE, border=AMBER, border_w=2, shadow=False)
    left_text(mod_x + 20, y + 15, title, F_BOX_TITLE, fill=NAVY)
    left_text(mod_x + 20, y + 58, sub, F_BOX_DETAIL, fill=SLATE)

# ═══════════════════════════════════════════════════════════════
# LAYER 4 — DATA LAYER
# ═══════════════════════════════════════════════════════════════
left_text(60, 720, "4. DATA & UTILITIES", F_SECTION, fill=SLATE)

# Google Sheets card
gs_x, gs_y, gs_w, gs_h = 60, 760, 580, 380
rounded_card(gs_x, gs_y, gs_w, gs_h, fill=WHITE, border=GREEN, border_w=3)
draw.rounded_rectangle([gs_x, gs_y, gs_x + gs_w, gs_y + 64], radius=18, fill=GREEN)
draw.rectangle([gs_x, gs_y + 40, gs_x + gs_w, gs_y + 64], fill=GREEN)
centered_text(gs_x + gs_w / 2, gs_y + 32, "Google Sheets API v4", F_BOX_TITLE, fill=WHITE)

# Tables inside
tb_x = gs_x + 30
tb_w = gs_w - 60
# customers table
rounded_card(tb_x, gs_y + 90, tb_w, 135, fill=(240, 253, 244), border=GREEN, border_w=2, shadow=False)
left_text(tb_x + 18, gs_y + 102, "customers  (read)", F_BOX_TITLE, fill=NAVY)
left_text(tb_x + 18, gs_y + 145, "phone_number  |  first_name  |  last_name  |  claim_status", F_BOX_DETAIL, fill=SLATE)
left_text(tb_x + 18, gs_y + 175, "Normalized to E.164 via Google phonenumbers library", F_BOX_DETAIL, fill=GREEN)

# interactions table
rounded_card(tb_x, gs_y + 240, tb_w, 125, fill=(240, 253, 244), border=GREEN, border_w=2, shadow=False)
left_text(tb_x + 18, gs_y + 252, "interactions  (write)", F_BOX_TITLE, fill=NAVY)
left_text(tb_x + 18, gs_y + 295, "timestamp  |  phone  |  summary  |  sentiment  |  transcript", F_BOX_DETAIL, fill=SLATE)
left_text(tb_x + 18, gs_y + 325, "Written once per call by end-of-call webhook", F_BOX_DETAIL, fill=GREEN)

# ═══════════════════════════════════════════════════════════════
# UTILITIES / CROSS-CUTTING
# ═══════════════════════════════════════════════════════════════
util_x, util_y, util_w, util_h = 700, 760, 540, 380
rounded_card(util_x, util_y, util_w, util_h, fill=WHITE, border=SLATE, border_w=2)
left_text(util_x + 25, util_y + 20, "Cross-Cutting Concerns", F_BOX_TITLE, fill=NAVY)
utilities = [
    ("Pydantic", "Strict webhook payload validation"),
    ("structlog", "JSON structured logging per call_id"),
    ("tenacity", "Exponential-backoff retries on API calls"),
    ("phonenumbers", "E.164 normalization for all lookups"),
    ("pytest", "48 unit tests, mocks OpenAI + Sheets"),
]
for i, (name, desc) in enumerate(utilities):
    y = util_y + 75 + i * 58
    # bullet
    draw.ellipse([util_x + 25, y + 10, util_x + 39, y + 24], fill=TEAL)
    left_text(util_x + 55, y, name, F_BOX_SUB, fill=NAVY)
    left_text(util_x + 200, y + 3, desc, F_BOX_DETAIL, fill=SLATE)

# ═══════════════════════════════════════════════════════════════
# EXTERNAL LLM (summarizer)
# ═══════════════════════════════════════════════════════════════
llm_x, llm_y, llm_w, llm_h = 1290, 760, 650, 380
rounded_card(llm_x, llm_y, llm_w, llm_h, fill=WHITE, border=NAVY, border_w=2)
left_text(llm_x + 25, llm_y + 20, "External APIs Used", F_BOX_TITLE, fill=NAVY)
apis = [
    ("OpenAI",     "GPT-4o",      "Live conversation LLM"),
    ("OpenAI",     "GPT-4o-mini", "Post-call summarizer (30× cheaper)"),
    ("Deepgram",   "Nova-2",      "Speech-to-text (English-locked)"),
    ("ElevenLabs", "Rachel",      "Text-to-speech synthesis"),
    ("Google",     "Sheets v4",   "Customer DB + interaction log"),
]
col1, col2, col3 = llm_x + 30, llm_x + 200, llm_x + 370
left_text(col1, llm_y + 75, "Vendor", F_ARROW, fill=SLATE)
left_text(col2, llm_y + 75, "Model / API", F_ARROW, fill=SLATE)
left_text(col3, llm_y + 75, "Purpose", F_ARROW, fill=SLATE)
draw.line([(llm_x + 25, llm_y + 105), (llm_x + llm_w - 25, llm_y + 105)], fill=CARD_BORDER, width=2)
for i, (v, m, p) in enumerate(apis):
    y = llm_y + 120 + i * 48
    left_text(col1, y, v, F_BOX_DETAIL, fill=NAVY)
    left_text(col2, y, m, F_BOX_DETAIL, fill=TEAL)
    left_text(col3, y, p, F_BOX_DETAIL, fill=SLATE)

# ═══════════════════════════════════════════════════════════════
# ARROWS BETWEEN LAYERS
# ═══════════════════════════════════════════════════════════════
# Caller → VAPI
arrow(caller_x + caller_w, caller_y + caller_h / 2,
      vapi_x, vapi_y + vapi_h / 2 - 60,
      color=TEAL, width=4, label="voice")

# VAPI → Backend (tool-calls + webhook)
arrow(vapi_x + vapi_w, vapi_y + vapi_h / 2 - 40,
      be_x, be_y + vapi_h / 2 - 40,
      color=AMBER, width=4, label="tool-calls")
arrow(vapi_x + vapi_w, vapi_y + vapi_h / 2 + 20,
      be_x, be_y + vapi_h / 2 + 20,
      color=AMBER, width=4, label="end-of-call")

# Backend → Sheets (down-left)
arrow(be_x + 200, be_y + be_h,
      gs_x + gs_w / 2 + 80, gs_y,
      color=GREEN, width=4, label="read / write")

# Backend → OpenAI summarizer (down)
arrow(be_x + be_w / 2 + 100, be_y + be_h,
      llm_x + llm_w / 2, llm_y,
      color=NAVY, width=3, label="summarize")

# ═══════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════
draw.rectangle([0, H - 60, W, H], fill=NAVY_DARK)
footer_text = "Voice in  →  VAPI orchestrates STT + LLM + TTS  →  tool-calls hit FastAPI  →  Sheets lookup  →  response spoken back  →  post-call webhook writes structured log"
centered_text(W / 2, H - 30, footer_text, F_FOOTER, fill=(165, 243, 252))

# ═══════════════════════════════════════════════════════════════
# SAVE
# ═══════════════════════════════════════════════════════════════
out_path = Path(__file__).resolve().parent.parent / "docs" / "architecture_diagram.png"
out_path.parent.mkdir(parents=True, exist_ok=True)
img.save(out_path, "PNG", optimize=True)
print(f"Saved: {out_path}")
print(f"Size:  {out_path.stat().st_size / 1024:.1f} KB")
print(f"Dims:  {W}x{H}")
