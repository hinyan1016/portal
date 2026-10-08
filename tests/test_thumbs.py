"""図解カード用サムネイルの切り出しを検証する。"""
import io

from PIL import Image

from scripts.build_thumbs import card_image, is_strip, og_image


def png(width, height, mode='RGB', color='white'):
    buffer = io.BytesIO()
    Image.new(mode, (width, height), color).save(buffer, 'PNG')
    return buffer.getvalue()


def test_tall_infographic_keeps_the_top_as_16_9_webp():
    source = Image.new('RGB', (1080, 1920), 'white')
    source.paste((200, 30, 30), (0, 0, 1080, 300))
    buffer = io.BytesIO()
    source.save(buffer, 'PNG')
    with Image.open(io.BytesIO(card_image(buffer.getvalue()))) as out:
        assert out.format == 'WEBP' and out.size == (800, 450)
        assert out.convert('RGB').getpixel((400, 40))[0] > 150
        assert out.convert('RGB').getpixel((400, 420))[1] > 230


def test_wide_image_is_center_cropped_and_small_image_is_not_enlarged():
    with Image.open(io.BytesIO(card_image(png(2000, 450)))) as out:
        assert out.size == (800, 450)
    with Image.open(io.BytesIO(card_image(png(640, 640)))) as out:
        assert out.size == (640, 360)


def test_title_strip_is_skipped_and_transparency_becomes_white():
    assert is_strip(png(1080, 194)) and not is_strip(png(768, 756))
    with Image.open(io.BytesIO(card_image(png(800, 900, 'RGBA', (0, 0, 0, 0))))) as out:
        assert min(out.convert('RGB').getpixel((10, 10))) >= 245


def test_share_image_is_a_top_crop_jpeg_never_enlarged():
    source = Image.new('RGB', (1080, 1920), 'white')
    source.paste((200, 30, 30), (0, 0, 1080, 200))
    buffer = io.BytesIO()
    source.save(buffer, 'PNG')
    with Image.open(io.BytesIO(og_image(buffer.getvalue()))) as out:
        assert out.format == 'JPEG' and out.size == (1080, 567)
        assert out.getpixel((540, 30))[0] > 150
    with Image.open(io.BytesIO(og_image(png(2400, 4000)))) as out:
        assert out.size == (1200, 630)

