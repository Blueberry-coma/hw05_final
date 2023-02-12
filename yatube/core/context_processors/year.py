from datetime import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    dt = datetime.now().year
    return {
        'year': dt
    }
