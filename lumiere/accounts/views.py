from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm
from .models import User

GENERIC_LOGIN_ERROR = "Invalid email or password."


def _safe_next(request):
    """Return the ?next= URL only if it points back to this site."""
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return nxt
    return None


def register(request):
    if request.user.is_authenticated:
        return redirect("catalog:home")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.create_user(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            name=form.cleaned_data["name"],
        )
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Account created. Welcome to Lumiere!")
        return redirect(_safe_next(request) or "catalog:home")

    return render(request, "accounts/register.html", {"form": form, "next": _safe_next(request) or ""})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("catalog:home")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        account = User.objects.filter(email=email).first()

        if account and account.is_locked:
            form.add_error(
                None,
                f"Too many failed attempts. Please try again in {User.LOCK_MINUTES} minutes.",
            )
        else:
            user = authenticate(request, email=email, password=password)
            if user is None:
                if account:
                    account.register_failed_login()
                # Same message whether the email or the password was wrong.
                form.add_error(None, GENERIC_LOGIN_ERROR)
            else:
                user.reset_failed_logins()
                login(request, user)
                messages.success(request, f"Welcome back, {user.name}.")
                return redirect(_safe_next(request) or "catalog:home")

    return render(request, "accounts/login.html", {"form": form, "next": _safe_next(request) or ""})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("catalog:home")
