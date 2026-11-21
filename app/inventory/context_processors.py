def branch_context(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    from .utils import get_user_branches, get_active_branch
    return {
        "user_branches": get_user_branches(request.user),
        "active_branch": get_active_branch(request),
    }