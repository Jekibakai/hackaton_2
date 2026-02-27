from django.shortcuts import render
from django.http import JsonResponse
from datetime import datetime, timedelta
import random
import json


def get_mock_live_data():
    """Симуляция live-данных потребления"""
    return {
        'kwh': round(random.uniform(42.5, 58.3), 1),
        'cost_tenge': round(random.uniform(2100, 2900), 0),
        'co2_saved': round(random.uniform(18.2, 24.6), 1),
    }


def get_chart_data():
    """Данные для графика: реальные + AI-прогноз"""
    now = datetime.now()
    labels = []
    real = []
    forecast = []

    for i in range(24):
        t = now.replace(hour=i, minute=0, second=0)
        labels.append(t.strftime('%H:00'))
        base = 30 + 20 * abs(i - 8) / 8 if i < 8 else max(25, 55 - (i - 8) * 1.5)
        actual = round(base + random.uniform(-3, 3), 1) if i <= now.hour else None
        predicted = round(base + random.uniform(-1, 1), 1)
        real.append(actual)
        forecast.append(predicted)

    return {'labels': labels, 'real': real, 'forecast': forecast}


def get_anomalies():
    return [
        {
            'time': '27.02 02:15',
            'block': 'Блок А',
            'description': 'Аномальный скачок потребления',
            'detail': 'Вероятность утечки воды: 85%',
            'probability': 85,
            'severity': 'high',
        },
        {
            'time': '26.02 18:42',
            'block': 'Блок В',
            'description': 'Нагрев сверх нормы (+4°C)',
            'detail': 'Возможно, термостат неисправен',
            'probability': 72,
            'severity': 'medium',
        },
        {
            'time': '26.02 11:20',
            'block': 'Столовая',
            'description': 'Освещение не выключено',
            'detail': 'Свет горел 3 часа после занятий',
            'probability': 99,
            'severity': 'low',
        },
        {
            'time': '25.02 07:55',
            'block': 'Спортзал',
            'description': 'Пиковая нагрузка вентиляции',
            'detail': 'Превышение нормы на 40%',
            'probability': 61,
            'severity': 'medium',
        },
    ]


def get_ai_tip():
    tips = [
        "На основе прогноза погоды (-15°C) система рекомендует закрыть жалюзи в северном крыле — это сохранит до 5% тепла.",
        "Анализ данных показывает: пик нагрузки в 07:45–08:15. Рекомендуется плавный запуск отопления с 07:00.",
        "Блок А потребляет на 12% больше нормы вторник/четверг. Возможная причина: кружки после уроков. Проверьте расписание.",
        "Оптимальная температура для учёбы — 20–22°C. Сейчас 24°C в кабинетах 201–205. Снизьте на 2°C → экономия 8%.",
    ]
    return random.choice(tips)


def get_class_ratings():
    classes = [
        {'name': '8А', 'current': 145.2, 'previous': 182.4},
        {'name': '9Б', 'current': 158.7, 'previous': 187.1},
        {'name': '7В', 'current': 171.3, 'previous': 196.8},
        {'name': '10А', 'current': 163.9, 'previous': 178.2},
        {'name': '6Б', 'current': 189.4, 'previous': 192.0},
        {'name': '11А', 'current': 201.1, 'previous': 198.5},
    ]
    for c in classes:
        c['savings'] = round((c['previous'] - c['current']) / c['previous'] * 100, 1)
        c['trees'] = max(0, int(c['savings'] * 0.3))
    return sorted(classes, key=lambda x: -x['savings'])


# ─── Views ───────────────────────────────────────────────

def get_blocks_data():
    return [
        {'name': 'А', 'kwh': 18.3, 'percent': 91, 'color': '#ff3b5c'},
        {'name': 'Б', 'kwh': 12.1, 'percent': 64, 'color': '#ffcc00'},
        {'name': 'В', 'kwh': 8.9,  'percent': 47, 'color': '#00e5a0'},
        {'name': 'Г', 'kwh': 13.6, 'percent': 72, 'color': '#0099ff'},
    ]


def get_week_data():
    return [
        {'day': 'Пн', 'kwh': 389, 'percent': 78},
        {'day': 'Вт', 'kwh': 312, 'percent': 65},
        {'day': 'Ср', 'kwh': 421, 'percent': 82},
        {'day': 'Чт', 'kwh': 356, 'percent': 71},
        {'day': 'Пт', 'kwh': 445, 'percent': 88},
        {'day': 'Сб', 'kwh': 218, 'percent': 45},
        {'day': 'Вс', 'kwh': 195, 'percent': 40},
    ]


def overview(request):
    live = get_mock_live_data()
    chart = get_chart_data()
    context = {
        'active_tab': 'overview',
        'live': live,
        'chart_json': json.dumps(chart),
        'blocks': get_blocks_data(),
        'week_data': get_week_data(),
    }
    return render(request, 'dashboard/overview.html', context)


def ai_intelligence(request):
    context = {
        'active_tab': 'ai',
        'anomalies': get_anomalies(),
        'ai_tip': get_ai_tip(),
    }
    return render(request, 'dashboard/ai_intelligence.html', context)


def gamification(request):
    ratings = get_class_ratings()
    school_savings = round(sum(c['savings'] for c in ratings) / len(ratings), 1)
    context = {
        'active_tab': 'gamification',
        'ratings': ratings,
        'school_savings': school_savings,
        'tree_level': min(5, int(school_savings / 3)),  # 0–5 уровней дерева
    }
    return render(request, 'dashboard/gamification.html', context)


# API endpoint для live-обновления карточек
def api_live(request):
    return JsonResponse(get_mock_live_data())