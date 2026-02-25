from math import sin, cos, pi
from PIL import Image, ImageDraw


def draw_star_points(center_x, center_y, outer_r, inner_r, n=5):
    """Координаты вершин пятиконечной звезды (outer и inner чередуются)."""
    points = []
    for i in range(n * 2):
        angle = -pi / 2 + i * (pi / n)  # начинаем сверху
        r = outer_r if i % 2 == 0 else inner_r
        x = center_x + r * cos(angle)
        y = center_y + r * sin(angle)
        points.append((x, y))
    return points


def draw_icon(size):
    """Рисует красную звезду на фоне белого круга."""
    # Прозрачный фон для иконки
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    padding = int(size * 0.05)
    center = size // 2
    radius = (size - padding * 2) // 2

    # Белый круг (фон)
    circle_coords = [
        center - radius,
        center - radius,
        center + radius,
        center + radius,
    ]
    white = (255, 255, 255)
    draw.ellipse(circle_coords, fill=white, outline=(200, 200, 200))

    # Красная звезда
    outer_r = radius * 0.9
    inner_r = radius * 0.35
    star_points = draw_star_points(center, center, outer_r, inner_r)
    red = (220, 20, 60)  # Crimson
    draw.polygon(star_points, fill=red, outline=(180, 0, 40))

    return img

# Размеры иконки
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
icons = [draw_icon(s[0]) for s in sizes]

# ICO поддерживает RGBA
try:
    icons[0].save(
        "app.ico",
        format="ICO",
        sizes=[(s[0], s[1]) for s in sizes],
        append_images=icons[1:],
    )
    print("OK: Иконка 'app.ico' создана!")
    print("    Дизайн: красная звезда на фоне белого круга")
except Exception as e:
    print(f"Ошибка при сохранении: {e}")
    try:
        icons[0].save("app.ico", format="ICO")
        print("OK: Иконка 'app.ico' создана (один размер)")
    except Exception as e2:
        print(f"Ошибка: {e2}")