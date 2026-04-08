from rest_framework.exceptions import PermissionDenied


def _get_allowed_nav_keys(request) -> set[str] | None:
    auth_payload = getattr(request, "auth", None)
    if not isinstance(auth_payload, dict):
        return None
    if "allowed_nav_keys" not in auth_payload:
        return None
    return set(auth_payload.get("allowed_nav_keys") or [])


def require_nav_access(request, nav_item_key: str, action: str = "view") -> None:
    if action != "view":
        raise PermissionDenied("Unsupported navigation policy action.")

    if getattr(request.user, "role", None) != "admin":
        return

    allowed_nav_keys = _get_allowed_nav_keys(request)
    if allowed_nav_keys is None:
        return

    if nav_item_key not in allowed_nav_keys:
        raise PermissionDenied("This API is not allowed by current navigation policy.")
