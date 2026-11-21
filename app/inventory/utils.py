from django.core.exceptions import PermissionDenied
from .models import Branch


def get_main_branch():
    """Ensure a Main branch exists; create if missing."""
    branch, _ = Branch.objects.get_or_create(
        name="Main Store & warehouse",
        defaults={"code": "MAIN", "is_active": True},
    )
    return branch


def get_user_branches(user):
    if not user.is_authenticated:
        return Branch.objects.none()

    # Superuser / role superuser → all active branches
    if user.is_superuser or getattr(user, "role", None) == "superuser":
        return Branch.objects.filter(is_active=True).order_by("name")

    qs = user.branches.filter(is_active=True).order_by("name")
    if qs.exists():
        return qs

    # Staff with zero branches → auto-assign Main
    main = get_main_branch()
    user.branches.add(main)
    return user.branches.filter(is_active=True).order_by("name")


def get_active_branch(request):
    user = request.user
    if not user.is_authenticated:
        return None

    allowed = get_user_branches(user)
    if not allowed.exists():
        return None

    branch_id = request.session.get("active_branch_id")
    if branch_id:
        branch = allowed.filter(pk=branch_id).first()
        if branch:
            return branch

    # Prefer last_branch if still allowed
    last_id = getattr(user, "last_branch_id", None)
    if last_id:
        branch = allowed.filter(pk=last_id).first()
        if branch:
            request.session["active_branch_id"] = branch.id
            return branch

    branch = allowed.first()
    request.session["active_branch_id"] = branch.id
    return branch


def require_active_branch(request):
    branch = get_active_branch(request)
    if branch is None:
        raise PermissionDenied("No branch available. Contact an administrator.")
    return branch


def products_qs(request):
    branch = require_active_branch(request)
    from .models import Product
    return Product.objects.filter(branch=branch)


def batches_qs(request):
    branch = require_active_branch(request)
    from .models import Batch
    return Batch.objects.filter(product__branch=branch)