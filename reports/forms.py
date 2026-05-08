from django import forms

from .models import Project, ProjectEvidence, ProjectReport, ReportComment


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

    def clean_sdg_tags(self):
        raw = (self.cleaned_data.get("sdg_tags") or "").strip()
        if not raw:
            return ""
        normalized = []
        for token in [x.strip() for x in raw.split(",") if x.strip()]:
            check = token.upper().replace(" ", "")
            if check.startswith("SDG"):
                suffix = check[3:]
                if suffix.isdigit() and 1 <= int(suffix) <= 17:
                    normalized.append(f"SDG {int(suffix)}")
                    continue
            raise forms.ValidationError("SDG tags must use SDG 1 to SDG 17 format (comma-separated).")
        return ", ".join(dict.fromkeys(normalized))

    def clean(self):
        cleaned = super().clean()
        planned = cleaned.get("budget_planned") or 0
        actual = cleaned.get("budget_actual") or 0
        if actual > planned and planned > 0:
            self.add_error("budget_actual", "Actual budget cannot exceed planned budget.")
        return cleaned


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


class ProjectEvidenceForm(forms.ModelForm):
    class Meta:
        model = ProjectEvidence
        fields = ["evidence_type", "title", "file", "external_url"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "external_url": forms.URLInput(attrs={"class": "form-control"}),
            "evidence_type": forms.Select(attrs={"class": "form-select"}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        file_obj = cleaned.get("file")
        external_url = cleaned.get("external_url")
        if not file_obj and not external_url:
            raise forms.ValidationError("Provide either a file or an external URL.")
        return cleaned


class ReviewActionForm(forms.Form):
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}))
