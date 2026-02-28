import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import datetime
import random
import json

from .models import ClassRating, Anomaly, Classroom


# ─── Mock helpers ────────────────────────────────────────

def get_mock_live_data():
    return {
        'kwh': round(random.uniform(42.5, 58.3), 1),
        'cost_tenge': round(random.uniform(2100, 2900), 0),
        'co2_saved': round(random.uniform(18.2, 24.6), 1),
    }


def get_chart_data():
    now = datetime.now()
    labels, real, forecast = [], [], []
    for i in range(24):
        labels.append(f"{i:02d}:00")
        base = 30 + 20 * abs(i - 8) / 8 if i < 8 else max(25, 55 - (i - 8) * 1.5)
        real.append(round(base + random.uniform(-3, 3), 1) if i <= now.hour else None)
        forecast.append(round(base + random.uniform(-1, 1), 1))
    return {'labels': labels, 'real': real, 'forecast': forecast}


def get_ai_tip():
    tips = [
        "На основе прогноза погоды (-15°C) система рекомендует закрыть жалюзи в северном крыле — это сохранит до 5% тепла.",
        "Анализ данных показывает: пик нагрузки в 07:45–08:15. Рекомендуется плавный запуск отопления с 07:00.",
        "Блок А потребляет на 12% больше нормы вторник/четверг. Возможная причина: кружки после уроков. Проверьте расписание.",
        "Оптимальная температура для учёбы — 20–22°C. Сейчас 24°C в кабинетах 201–205. Снизьте на 2°C → экономия 8%.",
    ]
    return random.choice(tips)


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


# Типы аномалий для симулятора
ANOMALY_TYPES = {
    'water_leak': {
        'description': 'Аномальный скачок потребления',
        'detail_tpl': 'Вероятность утечки воды: {prob}%',
        'severity': 'high',
        'prob_range': (75, 95),
    },
    'overheat': {
        'description': 'Нагрев сверх нормы',
        'detail_tpl': 'Превышение температуры на {delta}°C. Термостат может быть неисправен',
        'severity': 'medium',
        'prob_range': (55, 80),
    },
    'lights_on': {
        'description': 'Освещение не выключено',
        'detail_tpl': 'Свет горел {hours} часов после окончания занятий',
        'severity': 'low',
        'prob_range': (90, 99),
    },
    'ventilation': {
        'description': 'Пиковая нагрузка вентиляции',
        'detail_tpl': 'Превышение нормы на {pct}%',
        'severity': 'medium',
        'prob_range': (50, 75),
    },
    'door_open': {
        'description': 'Потеря тепла — открыт выход',
        'detail_tpl': 'Дверь открыта более {minutes} минут при температуре ниже -10°C',
        'severity': 'high',
        'prob_range': (80, 92),
    },
}

BLOCKS = ['Блок А', 'Блок Б', 'Блок В', 'Блок Г', 'Столовая', 'Спортзал', 'Библиотека']


def _seed_default_anomalies():
    """Заполнить БД дефолтными аномалиями если пустая"""
    from django.utils.timezone import make_aware
    defaults = [
        (datetime(2025, 2, 27, 2, 15), 'Блок А', 'Аномальный скачок потребления',
         'Вероятность утечки воды: 85%', 85, 'high'),
        (datetime(2025, 2, 26, 18, 42), 'Блок В', 'Нагрев сверх нормы',
         'Превышение температуры на 4°C. Термостат может быть неисправен', 72, 'medium'),
        (datetime(2025, 2, 26, 11, 20), 'Столовая', 'Освещение не выключено',
         'Свет горел 3 часа после окончания занятий', 99, 'low'),
        (datetime(2025, 2, 25, 7, 55), 'Спортзал', 'Пиковая нагрузка вентиляции',
         'Превышение нормы на 40%', 61, 'medium'),
    ]
    for ts, block, desc, detail, prob, sev in defaults:
        Anomaly.objects.create(
            timestamp=make_aware(ts),
            block=block,
            description=desc,
            detail=detail,
            probability=prob,
            severity=sev,
        )


def _seed_default_classes():
    defaults = [
        ('8А',  145.2, 182.4),
        ('9Б',  158.7, 187.1),
        ('7В',  171.3, 196.8),
        ('10А', 163.9, 178.2),
        ('6Б',  189.4, 192.0),
        ('11А', 201.1, 198.5),
    ]
    for name, curr, prev in defaults:
        obj = ClassRating(class_name=name, current_kwh=curr, previous_kwh=prev)
        obj.save()


# ─── Views ───────────────────────────────────────────────

def overview(request):
    context = {
        'active_tab': 'overview',
        'live': get_mock_live_data(),
        'chart_json': json.dumps(get_chart_data()),
        'blocks': get_blocks_data(),
        'week_data': get_week_data(),
    }
    return render(request, 'dashboard/overview.html', context)


def ai_intelligence(request):
    if not Anomaly.objects.exists():
        _seed_default_anomalies()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'simulate':
            block = request.POST.get('block', 'Блок А')
            atype = request.POST.get('anomaly_type', 'water_leak')
            cfg = ANOMALY_TYPES.get(atype, ANOMALY_TYPES['water_leak'])
            prob = random.randint(*cfg['prob_range'])

            # Генерируем detail с рандомными значениями
            detail = cfg['detail_tpl'].format(
                prob=prob,
                delta=random.randint(2, 8),
                hours=random.randint(2, 5),
                pct=random.randint(20, 60),
                minutes=random.randint(15, 45),
            )

            anomaly = Anomaly.objects.create(
                timestamp=timezone.now(),
                block=block,
                description=cfg['description'],
                detail=detail,
                probability=prob,
                severity=cfg['severity'],
            )

            # Если AJAX — возвращаем JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'id': anomaly.id,
                    'time': anomaly.timestamp.strftime('%d.%m %H:%M'),
                    'block': anomaly.block,
                    'description': anomaly.description,
                    'detail': detail,
                    'probability': anomaly.probability,
                    'severity': anomaly.severity,
                })

            messages.success(request, f'Аномалия создана: {cfg["description"]} в {block}')

        elif action == 'delete':
            pk = request.POST.get('pk')
            get_object_or_404(Anomaly, pk=pk).delete()
            messages.success(request, 'Аномалия удалена.')

        elif action == 'reset':
            Anomaly.objects.all().delete()
            _seed_default_anomalies()
            messages.success(request, 'Аномалии сброшены к демо-данным.')

        elif action == 'resolve':
            pk = request.POST.get('pk')
            anomaly = get_object_or_404(Anomaly, pk=pk)
            anomaly.resolved = not anomaly.resolved
            anomaly.save()

        return redirect('ai_intelligence')

    anomalies = Anomaly.objects.all()
    high_count = anomalies.filter(severity='high').count()

    context = {
        'active_tab': 'ai',
        'anomalies': anomalies,
        'anomaly_count': anomalies.count(),
        'high_count': high_count,
        'ai_tip': get_ai_tip(),
        'blocks': BLOCKS,
        'anomaly_types': ANOMALY_TYPES,
    }
    return render(request, 'dashboard/ai_intelligence.html', context)


def gamification(request):
    if not ClassRating.objects.exists():
        _seed_default_classes()

    ratings = list(ClassRating.objects.all())
    school_savings = round(sum(c.savings_percent for c in ratings) / len(ratings), 1) if ratings else 0

    context = {
        'active_tab': 'gamification',
        'ratings': ratings,
        'school_savings': school_savings,
        'tree_level': min(5, int(school_savings / 3)),
    }
    return render(request, 'dashboard/gamification.html', context)


def manage_classes(request):
    if not ClassRating.objects.exists():
        _seed_default_classes()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            class_name = request.POST.get('class_name', '').strip()
            current_kwh = request.POST.get('current_kwh', '').strip()
            previous_kwh = request.POST.get('previous_kwh', '').strip()
            errors = []
            if not class_name:
                errors.append('Введите название класса.')
            if ClassRating.objects.filter(class_name=class_name).exists():
                errors.append(f'Класс «{class_name}» уже существует.')
            try:
                current_kwh = float(current_kwh)
                previous_kwh = float(previous_kwh)
                if current_kwh <= 0 or previous_kwh <= 0:
                    errors.append('Показания должны быть больше нуля.')
            except (ValueError, TypeError):
                errors.append('Введите корректные числа.')
            if errors:
                for e in errors:
                    messages.error(request, e)
            else:
                obj = ClassRating(class_name=class_name, current_kwh=current_kwh, previous_kwh=previous_kwh)
                obj.save()
                messages.success(request, f'Класс «{class_name}» добавлен! Экономия: {obj.savings_percent}%')

        elif action == 'delete':
            obj = get_object_or_404(ClassRating, pk=request.POST.get('pk'))
            name = obj.class_name
            obj.delete()
            messages.success(request, f'Класс «{name}» удалён.')

        elif action == 'update':
            obj = get_object_or_404(ClassRating, pk=request.POST.get('pk'))
            try:
                obj.current_kwh = float(request.POST.get('current_kwh'))
                obj.previous_kwh = float(request.POST.get('previous_kwh'))
                obj.save()
                messages.success(request, f'Класс «{obj.class_name}» обновлён! Экономия: {obj.savings_percent}%')
            except (ValueError, TypeError):
                messages.error(request, 'Введите корректные числа.')

        elif action == 'reset':
            ClassRating.objects.all().delete()
            _seed_default_classes()
            messages.success(request, 'Данные сброшены к демо-значениям.')

        return redirect('manage_classes')

    ratings = list(ClassRating.objects.all())
    school_savings = round(sum(c.savings_percent for c in ratings) / len(ratings), 1) if ratings else 0
    context = {
        'active_tab': 'manage',
        'ratings': ratings,
        'school_savings': school_savings,
        'tree_level': min(5, int(school_savings / 3)),
    }
    return render(request, 'dashboard/manage_classes.html', context)


# ─── API ─────────────────────────────────────────────────

def api_live(request):
    return JsonResponse(get_mock_live_data())


def api_ratings(request):
    ratings = list(ClassRating.objects.values(
        'id', 'class_name', 'current_kwh', 'previous_kwh', 'savings_percent', 'trees_saved'
    ))
    school_savings = round(sum(r['savings_percent'] for r in ratings) / len(ratings), 1) if ratings else 0
    return JsonResponse({
        'ratings': ratings,
        'school_savings': school_savings,
        'tree_level': min(5, int(school_savings / 3)),
    })


def export_anomalies_csv(request):
    """Экспорт аномалий в CSV"""
    import csv
    from django.http import HttpResponse

    # Фильтры из GET-параметров
    severity = request.GET.get('severity', '')       # high / medium / low
    resolved = request.GET.get('resolved', '')       # 1 / 0

    anomalies = Anomaly.objects.all()
    if severity:
        anomalies = anomalies.filter(severity=severity)
    if resolved == '1':
        anomalies = anomalies.filter(resolved=True)
    elif resolved == '0':
        anomalies = anomalies.filter(resolved=False)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="anomalies.csv"'

    # UTF-8 BOM — чтобы Excel открывал кириллицу без проблем
    response.write('﻿')

    writer = csv.writer(response)
    writer.writerow(['Время', 'Блок', 'Описание', 'Детали', 'Вероятность %', 'Уровень', 'Статус'])

    severity_labels = {'high': 'Высокий', 'medium': 'Средний', 'low': 'Низкий'}

    for a in anomalies:
        writer.writerow([
            a.timestamp.strftime('%d.%m.%Y %H:%M'),
            a.block,
            a.description,
            a.detail,
            a.probability,
            severity_labels.get(a.severity, a.severity),
            'Решено' if a.resolved else 'Активна',
        ])

    return response


# ─── Classrooms ──────────────────────────────────────────

def _seed_default_classrooms():
    names = ['Каб. 101', 'Каб. 102', 'Каб. 201', 'Каб. 202', 'Каб. 301', 'Спортзал', 'Столовая']
    for name in names:
        Classroom.objects.get_or_create(name=name)


def classrooms(request):
    """Страница со списком кабинетов и их статусами"""
    from .models import Classroom
    if not Classroom.objects.exists():
        _seed_default_classrooms()

    rooms = Classroom.objects.all()
    lights_on  = rooms.filter(light_status='on').count()
    lights_off = rooms.filter(light_status='off').count()
    context = {
        'active_tab': 'classrooms',
        'rooms': rooms,
        'lights_on': lights_on,
        'lights_off': lights_off,
        'total': rooms.count(),
    }
    return render(request, 'dashboard/classrooms.html', context)


def api_classroom_status(request):
    """
    POST — скрипт с камерой шлёт статус:
      { "classroom": "Каб. 101", "person_detected": true, "status": "on" }

    GET  — фронтенд опрашивает все кабинеты
    """
    from .models import Classroom

    if request.method == 'POST':
        import json as _json
        try:
            data = _json.loads(request.body)
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        name            = data.get('classroom', '').strip()
        person_detected = bool(data.get('person_detected', False))
        status          = data.get('status', 'off')   # on / off / waiting

        if not name:
            return JsonResponse({'error': 'classroom required'}, status=400)

        room, _ = Classroom.objects.get_or_create(name=name)
        room.person_detected = person_detected
        room.light_status    = status
        if person_detected:
            room.last_seen = timezone.now()
        room.save()

        # Если свет выключился автоматически — создаём аномалию-уведомление
        if status == 'off' and not person_detected:
            # Не спамим — создаём не чаще раза в 5 минут для этого кабинета
            from datetime import timedelta
            recent = Anomaly.objects.filter(
                block=name,
                description='Свет выключен автоматически',
                timestamp__gte=timezone.now() - timedelta(minutes=5)
            ).exists()
            if not recent:
                Anomaly.objects.create(
                    timestamp=timezone.now(),
                    block=name,
                    description='Свет выключен автоматически',
                    detail=f'AI-камера не обнаружила людей в кабинете более 10 секунд',
                    probability=99,
                    severity='low',
                )

        return JsonResponse({
            'ok': True,
            'classroom': room.name,
            'light_status': room.light_status,
            'person_detected': room.person_detected,
        })

    # GET — отдаём все кабинеты
    rooms = list(Classroom.objects.values(
        'id', 'name', 'light_status', 'person_detected', 'updated_at'
    ))
    # Форматируем время
    for r in rooms:
        if r['updated_at']:
            r['updated_at'] = r['updated_at'].strftime('%H:%M:%S')
    return JsonResponse({'classrooms': rooms})
