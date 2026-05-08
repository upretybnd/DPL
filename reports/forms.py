from django import forms

from .models import Project, ProjectReport, ReportComment


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "branch",
            "title",
            "project_type",
            "sdg_tags",
            "event_date",
            "location",
            "budget_planned",
            "budget_actual",
            "beneficiaries_count",
            "volunteer_hours",
            "impact_summary",
        ]
        widgets = {
            "event_date": forms.DateInput(attrs={"type": "date"}),
            "impact_summary": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class ProjectReportForm(forms.ModelForm):
    class Meta:
        model = ProjectReport
        fields = [
            "report_period",
            "objectives",
            "outcomes",
            "challenges",
            "lessons_learned",
            "partner_organizations",
        ]
        widgets = {
            "objectives": forms.Textarea(attrs={"rows": 3}),
            "outcomes": forms.Textarea(attrs={"rows": 3}),
            "challenges": forms.Textarea(attrs={"rows": 3}),
            "lessons_learned": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class ReportCommentForm(forms.ModelForm):
    class Meta:
        model = ReportComment
        fields = ["comment", "is_internal"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["comment"].widget.attrs.setdefault("class", "form-control")
        self.fields["is_internal"].widget.attrs.setdefault("class", "form-check-input")
