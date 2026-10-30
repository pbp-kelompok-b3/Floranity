from django import forms

from .models import JournalLog


class JournalLogForm(forms.ModelForm):

    SECTION_FIELDS = (
        ("Activity Details", ("plant_name", "plant_species", "plant_type", "activity", "occurred_at")),
        (
            "Plant Health & Care",
            (
                "water_volume_ml",
                "fertilizer_type",
                "health_status",
                "health_tags",
                "weather_temperature_c",
                "weather_humidity_percent",
                "weather_rainfall_mm",
            ),
        ),
        ("Photos & Notes", ("photo", "notes")),
    )

    class Meta:
        model = JournalLog
        fields = (
            "plant_name",
            "plant_species",
            "plant_type",
            "activity",
            "occurred_at",
            "water_volume_ml",
            "fertilizer_type",
            "health_status",
            "health_tags",
            "weather_temperature_c",
            "weather_humidity_percent",
            "weather_rainfall_mm",
            "photo",
            "notes",
        )
        widgets = {
            "occurred_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "health_tags": forms.TextInput(attrs={"placeholder": "e.g. new growth, yellow leaves"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
            "weather_temperature_c": forms.NumberInput(attrs={"step": "0.01"}),
            "weather_humidity_percent": forms.NumberInput(attrs={"min": 0, "max": 100}),
            "weather_rainfall_mm": forms.NumberInput(attrs={"step": "0.01", "min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in (
            "weather_temperature_c",
            "weather_humidity_percent",
            "weather_rainfall_mm",
        ):
            self.fields[field_name].disabled = True

    @property
    def sections(self):
        return [
            (title, [self[name] for name in field_names])
            for title, field_names in self.SECTION_FIELDS
        ]

    def save_for_owner(self, owner, plant=None, commit=True):
        instance = self.save(commit=False)
        instance.owner = owner
        instance.plant = plant
        if commit:
            instance.save()
            self.save_m2m()
        return instance
