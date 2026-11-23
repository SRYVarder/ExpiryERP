# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import Q

from .forms import SuperUserCreationForm, SuperUserChangeForm
from .models import CustomUser


def is_superuser(user):
    """Allow role=superuser OR Django is_superuser flag."""
    return user.is_authenticated and (
        user.is_superuser or getattr(user, "role", None) == "superuser"
    )


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("inventory:dashboard")
    return redirect("login")


# ===================== USER MANAGEMENT =====================

@user_passes_test(is_superuser, login_url="login")
def user_list(request):
    users = (
        CustomUser.objects.all()
        .prefetch_related("branches")
        .order_by("-date_joined")
    )

    search_query = request.GET.get("search", "").strip()
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
        )

    return render(
        request,
        "core/user_list.html",
        {
            "users": users,
            "search_query": search_query,
            "total_count": users.count(),
        },
    )


@user_passes_test(is_superuser, login_url="login")
def user_create(request):
    if request.method == "POST":
        form = SuperUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # branches set inside form.save()
            messages.success(
                request,
                f"User '{user.username}' created successfully "
                f"with role: {user.get_role_display()}.",
            )
            return redirect("core:user_list")
    else:
        form = SuperUserCreationForm()

    return render(request, "core/user_create.html", {"form": form})


@user_passes_test(is_superuser, login_url="login")
def user_update(request, pk):
    user_obj = get_object_or_404(CustomUser, pk=pk)

    if request.method == "POST":
        form = SuperUserChangeForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()  # branches migrated inside form.save()
            messages.success(
                request,
                f"User '{user_obj.username}' updated successfully!",
            )
            return redirect("core:user_list")
    else:
        form = SuperUserChangeForm(instance=user_obj)

    return render(
        request,
        "core/user_update.html",
        {"form": form, "user_obj": user_obj},
    )


@user_passes_test(is_superuser, login_url="login")
def user_delete(request, pk):
    user_obj = get_object_or_404(CustomUser, pk=pk)

    if request.method == "POST":
        if user_obj == request.user:
            messages.error(request, "You cannot delete yourself!")
        else:
            username = user_obj.username
            user_obj.delete()
            messages.success(request, f"User '{username}' deleted successfully!")
        return redirect("core:user_list")

    return render(
        request,
        "core/user_confirm_delete.html",
        {"object": user_obj},
    )


# ===================== API VIEWS (JWT) =====================
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # Prefer token user, not request.user (often anonymous on obtain)
            from rest_framework_simplejwt.tokens import AccessToken
            from django.contrib.auth import get_user_model

            User = get_user_model()
            try:
                token = AccessToken(response.data["access"])
                user = User.objects.get(id=token["user_id"])
                response.data["user"] = {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "full_name": user.get_full_name() or user.username,
                    "branch_ids": list(
                        user.branches.values_list("id", flat=True)
                    )
                    if not user.is_superuser
                    else "all",
                }
            except Exception:
                pass
        return response