#!/usr/bin/env python3
"""Draws the stream graphics for the OBS scenes (854x480): bg.png, overlay.png (transparent frame + top bar + side panel + LIVE badge, with a hole where the
video goes), starting.png, brb.png. Needs Pillow and the DejaVu fonts.   python3 make_overlay.py OUTDIR"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 854, 480
VX, VY, VW, VH = 16, 56, 570, 384          # the video window
PX, PY, PW, PH = 602, 56, 236, 384         # the side panel
CY, VI = (34, 211, 238), (139, 92, 246)    # accent cyan, violet
BOLD, REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(size, bold=True):
    return ImageFont.truetype(BOLD if bold else REG, size)


def grad(w, h, c1, c2, diag=True):
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            t = (x / w * 0.6 + y / h * 0.4) if diag else x / w
            px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
    return im


def text_grad(txt, size, c1=CY, c2=VI):
    f = font(size)
    box = f.getbbox(txt)
    w, h = box[2] + 6, box[3] + 6
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).text((2, 0), txt, font=f, fill=255)
    g = grad(w, h, c1, c2, diag=False).convert("RGBA")
    g.putalpha(m)
    return g


def logo(size):
    """Beam wordmark: a small light-beam mark + gradient text."""
    t = text_grad("Beam", size)
    mark = Image.new("RGBA", (size + 8, size + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(mark)
    s = size + 8
    d.ellipse((2, s // 2 - 6, 14, s // 2 + 6), fill=CY + (255,))
    d.polygon([(10, s // 2 - 4), (s - 2, 2), (s - 2, s - 2), (10, s // 2 + 4)], fill=(120, 215, 255, 235))
    out = Image.new("RGBA", (mark.width + 8 + t.width, max(mark.height, t.height)), (0, 0, 0, 0))
    out.paste(mark, (0, (out.height - mark.height) // 2), mark)
    out.paste(t, (mark.width + 8, (out.height - t.height) // 2), t)
    return out


def background():
    bg = grad(W, H, (8, 11, 28), (28, 20, 78)).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse((520, -140, 980, 260), fill=CY + (95,))
    d.ellipse((-160, 280, 320, 640), fill=VI + (110,))
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    bg = Image.alpha_composite(bg, glow)
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(rays)
    for x0, a in ((140, 26), (330, 20), (560, 24), (740, 18)):
        d.polygon([(x0, 0), (x0 + 46, 0), (x0 - 260, H), (x0 - 330, H)], fill=(180, 230, 255, a))
    return Image.alpha_composite(bg, rays.filter(ImageFilter.GaussianBlur(6)))


def overlay():
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    d.rectangle((0, 0, W, 44), fill=(6, 9, 22, 215))                       # top bar
    d.rectangle((0, 44, W, 45), fill=CY + (110,))
    o.alpha_composite(logo(24), (14, 8))
    d.text((156, 15), "room live test", font=font(13, False), fill=(160, 170, 205, 255))
    d.rounded_rectangle((W - 108, 10, W - 16, 34), radius=12, fill=(226, 54, 70, 255))   # LIVE badge
    d.ellipse((W - 98, 18, W - 90, 26), fill=(255, 255, 255, 255))
    d.text((W - 83, 14), "LIVE", font=font(13), fill=(255, 255, 255, 255))
    # glowing frame with a transparent hole for the video
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((VX - 6, VY - 6, VX + VW + 6, VY + VH + 6), radius=18, outline=CY + (210,), width=6)
    o = Image.alpha_composite(o, glow.filter(ImageFilter.GaussianBlur(7)))
    ring = grad(VW + 8, VH + 8, CY, VI).convert("RGBA")
    mask = Image.new("L", ring.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, ring.width - 1, ring.height - 1), radius=14, fill=255)
    ring.putalpha(mask)
    o.alpha_composite(ring, (VX - 4, VY - 4))
    hole = Image.new("L", (W, H), 255)
    ImageDraw.Draw(hole).rounded_rectangle((VX, VY, VX + VW, VY + VH), radius=10, fill=0)
    a = o.getchannel("A")
    a.paste(0, mask=Image.eval(hole, lambda v: 255 - v))
    o.putalpha(a)
    d = ImageDraw.Draw(o)
    # side panel
    d.rounded_rectangle((PX, PY, PX + PW, PY + PH), radius=14, fill=(12, 17, 40, 225), outline=(90, 100, 170, 140), width=1)
    d.text((PX + 16, PY + 16), "LIVE ON BEAM", font=font(11), fill=CY + (255,))
    d.text((PX + 16, PY + 36), "Discord stage", font=font(21), fill=(255, 255, 255, 255))
    y = PY + 76
    for line in ("Video travels as Beam", "room messages: small", "encrypted pieces, no", "CDN in between."):
        d.text((PX + 16, y), line, font=font(12, False), fill=(185, 195, 225, 255)); y += 18
    d.line((PX + 16, PY + 168, PX + PW - 16, PY + 168), fill=(90, 100, 170, 140))
    d.text((PX + 16, PY + 180), "STATUS", font=font(11), fill=CY + (255,))               # the live text (status.txt) is drawn by OBS at PY+198
    d.line((PX + 16, PY + 300, PX + PW - 16, PY + 300), fill=(90, 100, 170, 140))
    d.text((PX + 16, PY + 312), "CHANNEL", font=font(11), fill=CY + (255,))
    d.text((PX + 16, PY + 330), "stream / messages", font=font(14), fill=(255, 255, 255, 255))
    d.text((PX + 16, PY + 352), "end-to-end encrypted", font=font(11, False), fill=(150, 160, 195, 255))
    t = "Delivered over Beam rooms"
    d.text(((W - d.textlength(t, font=font(12, False))) // 2, 454), t, font=font(12, False), fill=(150, 160, 200, 255))
    return o


def overlay_min():
    """Fullscreen scenes: only a small logo chip (top-left) and a LIVE badge (top-right) over the video."""
    o = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(o)
    d.rounded_rectangle((10, 10, 128, 44), radius=17, fill=(6, 9, 22, 175))
    o.alpha_composite(logo(20), (20, 14))
    d.rounded_rectangle((W - 92, 14, W - 12, 38), radius=12, fill=(226, 54, 70, 235))
    d.ellipse((W - 82, 22, W - 74, 30), fill=(255, 255, 255, 255))
    d.text((W - 67, 18), "LIVE", font=font(13), fill=(255, 255, 255, 255))
    return o


def title_card(big, small):
    c = background()
    lg = logo(84)
    c.alpha_composite(lg, ((W - lg.width) // 2, 150))
    d = ImageDraw.Draw(c)
    d.text(((W - d.textlength(big, font=font(30))) // 2, 276), big, font=font(30), fill=(255, 255, 255, 255))
    d.text(((W - d.textlength(small, font=font(14, False))) // 2, 322), small, font=font(14, False), fill=(170, 180, 215, 255))
    d.rounded_rectangle((W // 2 - 60, 360, W // 2 + 60, 364), radius=2, fill=CY + (255,))
    return c


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "overlay_assets"
    os.makedirs(out, exist_ok=True)
    background().convert("RGB").save(f"{out}/bg.png")
    overlay().save(f"{out}/overlay.png")
    overlay_min().save(f"{out}/overlay_min.png")
    title_card("Starting soon", "a live test over Beam rooms").convert("RGB").save(f"{out}/starting.png")
    title_card("Be right back", "the stream will resume shortly").convert("RGB").save(f"{out}/brb.png")
    print("wrote", sorted(os.listdir(out)))
