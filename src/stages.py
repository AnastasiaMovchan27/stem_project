"""Запуск стадій за назвою: єдине місце, де назви стадій з config.json з'єднано з функціями."""
from src import filtering, fourier, histogram, retouch

# Категорія кожної стадії (для перевірки: пайплайн має містити стадії щонайменше з 3 різних категорій)
CATEGORIES = {
    "bilateral": "Фільтрація",
    "diffusion": "Фільтрація",
    "clahe": "Гістограмна корекція",
    "equalize": "Гістограмна корекція",
    "unsharp": "Ретушування та покращення",
    "inpaint": "Ретушування та покращення",
    "wiener": "Перетворення Фур'є",
    "stretch": "Регулювання яскравості та контрасту",
}


def run_stage(name, image, params):
    """Застосовує стадію name до зображення; params - параметри цієї стадії з розділу stages."""
    if name == "bilateral":
        return filtering.bilateral_filter(
            image, params["radius"], params["sigma_space"], params["sigma_range"])
    if name == "diffusion":
        return filtering.anisotropic_diffusion(
            image, params["iterations"], params["kappa"], params.get("gamma", 0.2))
    if name == "clahe":
        return histogram.clahe(
            image, params["tiles"], params["clip_limit"], params.get("range_threshold"))
    if name == "equalize":
        return histogram.equalize_histogram(image)
    if name == "unsharp":
        return retouch.unsharp_mask(
            image, params["amount"], params["sigma"], params.get("threshold", 0.0),
            params.get("noise_factor", 0.0))
    if name == "inpaint":
        return retouch.impulse_inpaint(image, params["max_window"])
    if name == "wiener":
        return fourier.spectral_wiener(image, params["strength"], params.get("pad", 16))
    if name == "stretch":
        return histogram.contrast_stretch(
            image, params.get("low_percentile", 0.0), params.get("high_percentile", 100.0),
            params.get("range_threshold"))
    # сюди додаються нові стадії (функція в модулі + гілка тут + назва в config.json)
    raise ValueError("Невідома стадія: " + str(name))
