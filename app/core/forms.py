from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import MinimumLengthValidator

from inventory.models import Branch

User = get_user_model()


BRANCH_WIDGET_CLASS = (
    "bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 w-full text-white "
    "focus:outline-none focus:border-teal-500"
)


class SuperUserCreationForm(UserCreationForm):
    """
    Create staff accounts and assign one or more branches.
    Role "superuser" does not require branches (sees all).
    """
    branches = forms.ModelMultipleChoiceField(
        queryset=Branch.objects.filter(is_active=True).order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select warehouses this user can access. Required unless role is superuser.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "role", "branches")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "branches":
                continue
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} {BRANCH_WIDGET_CLASS}".strip()

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        branches = cleaned.get("branches")

        if role != "superuser" and not branches:
            self.add_error(
                "branches",
                "Select at least one branch for non-superuser accounts.",
            )
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)

        if self.cleaned_data.get("role") == "superuser":
            user.is_superuser = True
            user.is_staff = True

        if commit:
            user.save()
            if user.is_superuser or self.cleaned_data.get("role") == "superuser":
                user.branches.clear()
            else:
                user.branches.set(self.cleaned_data.get("branches") or [])
        return user


class SuperUserChangeForm(forms.ModelForm):
    """
    Update user, optional password change, and migrate branch assignments.
    """
    password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={"class": BRANCH_WIDGET_CLASS}),
        required=False,
        help_text="Leave blank if you don't want to change the password.",
        validators=[MinimumLengthValidator(6)],
    )
    password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={"class": BRANCH_WIDGET_CLASS}),
        required=False,
    )
    branches = forms.ModelMultipleChoiceField(
        queryset=Branch.objects.filter(is_active=True).order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Change which warehouses this user can access. Superusers ignore this list.",
    )

    class Meta:
        model = User
        fields = ("username", "email", "role", "branches")
        # Add "is_active" here if your CustomUser has it and you want it on the form

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in ("branches", "password1", "password2"):
                continue
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} {BRANCH_WIDGET_CLASS}".strip()

        if self.instance and self.instance.pk:
            self.fields["branches"].initial = self.instance.branches.all()

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")

        if (p1 and not p2) or (p2 and not p1):
            raise forms.ValidationError(
                "You must fill out both password fields to change the account password."
            )
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("The two password fields do not match.")

        role = cleaned_data.get("role")
        branches = cleaned_data.get("branches")
        is_su = (
            role == "superuser"
            or (self.instance and self.instance.is_superuser)
        )
        if not is_su and not branches:
            self.add_error(
                "branches",
                "Select at least one branch for non-superuser accounts.",
            )
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        p1 = self.cleaned_data.get("password1")
        if p1:
            user.set_password(p1)

        role = self.cleaned_data.get("role")
        if role == "superuser":
            user.is_superuser = True
            user.is_staff = True

        if commit:
            user.save()
            if user.is_superuser or role == "superuser":
                user.branches.clear()
            else:
                user.branches.set(self.cleaned_data.get("branches") or [])
                # If last_branch is no longer allowed, move to first assigned
                if getattr(user, "last_branch_id", None):
                    if not user.branches.filter(pk=user.last_branch_id).exists():
                        user.last_branch = user.branches.order_by("name").first()
                        user.save(update_fields=["last_branch"])
        return user