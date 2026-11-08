"""Метрики якості, написані вручну: MSE, PSNR і SSIM."""
import math

MAX_VALUE = 255.0


def mse(image_a, image_b):
    """Середня квадратична похибка: MSE = 1/(N*M) * сума (a - b)^2."""
    if image_a.shape != image_b.shape:
        raise ValueError("Зображення мають різні розміри")
    height, width = image_a.shape
    total = 0.0
    for i in range(height):
        for j in range(width):
            difference = image_a[i, j] - image_b[i, j]
            total = total + difference * difference
    return total / (height * width)


def psnr(mse_value):
    """Піковий сигнал/шум у децибелах: PSNR = 10 * lg(255^2 / MSE). Для MSE = 0 повертає inf."""
    if mse_value == 0:
        return math.inf
    return 10.0 * math.log10(MAX_VALUE * MAX_VALUE / mse_value)


def ssim(image_a, image_b, window=8, step=4):
    """Індекс структурної подібності (SSIM), усереднений по вікнах window x window з кроком step.

    Для одного вікна: ((2 mx my + C1)(2 cov + C2)) / ((mx^2 + my^2 + C1)(vx + vy + C2)),
    де mx, my - середні, vx, vy - дисперсії, cov - коваріація, C1 = (0,01*255)^2, C2 = (0,03*255)^2.
    """
    if image_a.shape != image_b.shape:
        raise ValueError("Зображення мають різні розміри")
    height, width = image_a.shape
    window = min(window, height, width)  # для малих зображень беремо все зображення
    c1 = (0.01 * MAX_VALUE) ** 2
    c2 = (0.03 * MAX_VALUE) ** 2
    total = 0.0
    count = 0
    for top in range(0, height - window + 1, step):
        for left in range(0, width - window + 1, step):
            part_a = image_a[top:top + window, left:left + window]
            part_b = image_b[top:top + window, left:left + window]
            mean_a = part_a.mean()
            mean_b = part_b.mean()
            var_a = ((part_a - mean_a) ** 2).mean()
            var_b = ((part_b - mean_b) ** 2).mean()
            cov = ((part_a - mean_a) * (part_b - mean_b)).mean()
            numerator = (2 * mean_a * mean_b + c1) * (2 * cov + c2)
            denominator = (mean_a ** 2 + mean_b ** 2 + c1) * (var_a + var_b + c2)
            total = total + numerator / denominator
            count = count + 1
    return total / count


def compare(image_a, image_b, window=8, step=4):
    """Повертає словник з MSE, PSNR і SSIM для двох зображень."""
    error = mse(image_a, image_b)
    return {"mse": error, "psnr": psnr(error), "ssim": ssim(image_a, image_b, window, step)}
