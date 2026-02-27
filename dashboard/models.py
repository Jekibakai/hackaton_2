from django.db import models


# потребббление энерггии
class EnergyReading(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    block = models.CharField(max_length=50, default='Блок А')
    kwh = models.FloatField()
    cost_tenge = models.FloatField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.block} — {self.kwh} кВт/ч @ {self.timestamp}"


# Обнаружение хуйни
class Anomaly(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Низкая'),
        ('medium', 'Средняя'),
        ('high', 'Высокая'),
    ]
    timestamp = models.DateTimeField()
    block = models.CharField(max_length=50)
    description = models.TextField()
    probability = models.IntegerField(help_text='Вероятность в %')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.block} — {self.description[:50]}"


# гейификация
class ClassRating(models.Model):
    class_name = models.CharField(max_length=20)
    current_kwh = models.FloatField()
    previous_kwh = models.FloatField()
    savings_percent = models.FloatField()
    trees_saved = models.IntegerField(default=0)

    class Meta:
        ordering = ['-savings_percent']

    def __str__(self):
        return f"{self.class_name} — {self.savings_percent}%"