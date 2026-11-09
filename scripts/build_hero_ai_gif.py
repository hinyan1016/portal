"""画像生成した本・AIチップを合成し、継ぎ目のない5秒のGIFを書き出す。"""
from pathlib import Path
import json
import math
from PIL import Image, ImageDraw, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs' / 'hero-ai-knowledge-20261110'
SIZE = (576, 384)
SECONDS = 5
FPS = 20


def sparkle(canvas, x, y, radius, strength):
    """小さな星の光。点滅させず、強弱をなめらかにつなぐ。"""
    layer = Image.new('RGBA', canvas.size)
    draw = ImageDraw.Draw(layer)
    points = []
    for i in range(8):
        angle = -math.pi / 2 + i * math.pi / 4
        r = radius if i % 2 == 0 else radius * .25
        points.append((x + math.cos(angle) * r, y + math.sin(angle) * r))
    draw.polygon(points, fill=(243, 178, 43, round(255 * strength)))
    draw.line([(x, y-radius*.56), (x, y+radius*.56)],
              fill=(255, 245, 193, round(220*strength)), width=2)
    canvas.alpha_composite(layer)


def build():
    SOURCE.mkdir(parents=True, exist_ok=True)
    plate = Image.open(SOURCE / 'book-layer.png').convert('RGBA').resize(SIZE, Image.Resampling.LANCZOS)
    raw_chip = Image.open(SOURCE / 'chip-layer.png').convert('RGBA')
    # 生成時の余白に依存せず、透過したチップ本体のサイズをそろえる。
    mask = raw_chip.getchannel('A').point(lambda a: 255 if a > 30 else 0)
    bounds = mask.getbbox()
    if not bounds:
        raise ValueError('AIチップの透過レイヤーが空です')
    chip = raw_chip.crop(bounds).resize((170, 165), Image.Resampling.LANCZOS)
    frames = []
    for frame in range(SECONDS * FPS):
        phase = 2 * math.pi * frame / (SECONDS * FPS)
        canvas = plate.copy()
        # t=0 と t=5 は位置・速度とも一致する周期運動。
        chip_y = 36 + 9 * math.sin(phase)
        canvas.alpha_composite(chip, (252, round(chip_y)))
        for x, y, radius, offset in [(240, 48, 16, 0), (438, 64, 12, 2),
                                      (438, 173, 10, 4), (204, 90, 8, 1)]:
            strength = .65 + .25 * math.sin(phase + offset)
            sparkle(canvas, x, y, radius * (.88 + .12*math.sin(phase+offset)), strength)
        # 本からAIへ向かう、小さな光の粒。始点・終点では消えるので継ぎ目がない。
        for offset in [0, .5]:
            progress = (frame/(SECONDS*FPS) + offset) % 1
            x = 287 + 39 * progress
            y = 248 - 62 * progress
            opacity = int(170 * math.sin(math.pi*progress)**2)
            particles = Image.new('RGBA', SIZE)
            d = ImageDraw.Draw(particles)
            d.ellipse((x-2, y-2, x+2, y+2), fill=(230, 166, 43, opacity))
            canvas.alpha_composite(particles)
        frames.append(canvas.convert('RGB'))

    # 全フレームで共通のパレットを使い、GIF特有の色揺れを防ぐ。
    palette_source = Image.new('RGB', (SIZE[0], SIZE[1]*10))
    for i in range(10):
        palette_source.paste(frames[i*10], (0, SIZE[1]*i))
    palette = palette_source.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in frames]
    gif_path = ROOT / 'assets' / 'hero-ai-knowledge.gif'
    indexed[0].save(gif_path, save_all=True, append_images=indexed[1:],
                    duration=1000//FPS, loop=0, disposal=1, optimize=True)
    frames[0].save(ROOT / 'assets' / 'hero-ai-knowledge.webp', quality=90, method=6)
    sheet = Image.new('RGB', (SIZE[0]*3, SIZE[1]*2), '#faf6ef')
    for i, index in enumerate([0, 20, 40, 60, 80, 99]):
        sheet.paste(frames[index], (SIZE[0]*(i%3), SIZE[1]*(i//3)))
    sheet.save(SOURCE / 'contact-sheet.jpg', quality=90)
    gif = Image.open(gif_path)
    durations = []
    for i in range(gif.n_frames):
        gif.seek(i)
        durations.append(gif.info['duration'])
    seam = ImageStat.Stat(ImageChops.difference(frames[0], frames[-1]))
    report = {'size': list(SIZE), 'frames': gif.n_frames, 'loop': gif.info.get('loop'),
              'duration_ms': sum(durations), 'bytes': gif_path.stat().st_size,
              'seam_mean_rgb_difference': seam.mean, 'chip_source_bounds': bounds}
    assert report['loop'] == 0 and report['frames'] > 1 and sum(durations) == SECONDS*1000
    (SOURCE / 'gif-qa.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    build()
