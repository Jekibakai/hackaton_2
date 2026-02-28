from django.db import models


class EnergyReading(models.Model):
    """Показания потребления энергии"""
    timestamp = models.DateTimeField(auto_now_add=True)
    block = models.CharField(max_length=50, default='Блок А')
    kwh = models.FloatField()
    cost_tenge = models.FloatField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.block} — {self.kwh} кВт/ч @ {self.timestamp}"


class Anomaly(models.Model):
    """AI-обнаруженные аномалии"""
    SEVERITY_CHOICES = [
        ('low', 'Низкая'),
        ('medium', 'Средняя'),
        ('high', 'Высокая'),
    ]
    timestamp = models.DateTimeField()
    block = models.CharField(max_length=50)
    description = models.TextField()
    detail = models.TextField(blank=True, default="", verbose_name="Детали")
    probability = models.IntegerField(help_text='Вероятность в %')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.block} — {self.description[:50]}"


class ClassRating(models.Model):
    """Рейтинг классов для геймификации"""
    class_name = models.CharField(max_length=20, verbose_name='Класс')
    current_kwh = models.FloatField(verbose_name='Потребление (тек. месяц, кВт)')
    previous_kwh = models.FloatField(verbose_name='Потребление (пред. месяц, кВт)')
    savings_percent = models.FloatField(default=0, verbose_name='Экономия %')
    trees_saved = models.IntegerField(default=0, verbose_name='Деревьев')

    class Meta:
        ordering = ['-savings_percent']
        verbose_name = 'Рейтинг класса'
        verbose_name_plural = 'Рейтинг классов'

    def save(self, *args, **kwargs):
        # Автоматически считаем savings_percent и trees при сохранении
        if self.previous_kwh and self.previous_kwh > 0:
            self.savings_percent = round(
                (self.previous_kwh - self.current_kwh) / self.previous_kwh * 100, 1
            )
        else:
            self.savings_percent = 0
        self.trees_saved = max(0, int(self.savings_percent * 0.3))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.class_name} — {self.savings_percent}%"


class Classroom(models.Model):
    """Кабинет с камерой и датчиком присутствия"""
    LIGHT_CHOICES = [
        ('on',      'Свет включён'),
        ('off',     'Свет выключен'),
        ('waiting', 'Ожидание...'),
    ]

    name = models.CharField(max_length=50, unique=True, verbose_name='Кабинет')
    light_status = models.CharField(
        max_length=10, choices=LIGHT_CHOICES, default='off', verbose_name='Статус света'
    )
    person_detected = models.BooleanField(default=False, verbose_name='Есть люди')
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name='Последнее обнаружение')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        ordering = ['name']
        verbose_name = 'Кабинет'
        verbose_name_plural = 'Кабинеты'

    def __str__(self):
        return f"{self.name} — {self.get_light_status_display()}"
