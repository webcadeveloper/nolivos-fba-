"""
Decoradores de permisos para proteger rutas Flask.

Uso:
    from src.auth.decorators import login_required, role_required, permission_required

    @app.route("/admin")
    @login_required
    @role_required('owner')
    def admin_panel():
        return "Admin panel"

    @app.route("/scan")
    @login_required
    @permission_required('scan_products')
    def scan_products():
        return "Scanning..."
"""

from functools import wraps
from flask import redirect, url_for, flash, request, abort
from flask_login import current_user


def login_required(f):
    """
    Decorator que requiere que el usuario esté autenticado.
    Redirige a login si no está autenticado.

    Nota: Flask-Login ya provee @login_required, pero este
    añade mensajes flash y mejor UX.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Por favor inicia sesión para acceder a esta página', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """
    Decorator que requiere que el usuario tenga uno de los roles especificados.

    Args:
        *roles: Uno o más roles permitidos (ej: 'owner', 'analyst')

    Ejemplo:
        @role_required('owner')
        @role_required('owner', 'analyst')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Por favor inicia sesión para acceder a esta página', 'warning')
                return redirect(url_for('login', next=request.url))

            if current_user.role not in roles:
                flash(f'Acceso denegado. Rol requerido: {", ".join(roles)}', 'danger')
                abort(403)  # Forbidden

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permission_required(permission):
    """
    Decorator que requiere que el usuario tenga un permiso específico.

    Args:
        permission: Nombre del permiso requerido (ej: 'scan_products', 'manage_webhooks')

    Ejemplo:
        @permission_required('scan_products')
        def scan_route():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Por favor inicia sesión para acceder a esta página', 'warning')
                return redirect(url_for('login', next=request.url))

            if not current_user.has_permission(permission):
                flash(f'No tienes permiso para: {permission}', 'danger')
                abort(403)  # Forbidden

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def owner_required(f):
    """
    Decorator que requiere que el usuario sea owner.
    Shortcut para @role_required('owner')
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Por favor inicia sesión para acceder a esta página', 'warning')
            return redirect(url_for('login', next=request.url))

        if current_user.role != 'owner':
            flash('Solo el Owner puede acceder a esta funcionalidad', 'danger')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function


def same_workspace_required(f):
    """
    Decorator que verifica que el recurso solicitado pertenece
    al mismo workspace del usuario actual.

    Útil para prevenir acceso cross-workspace.

    La función decorada debe retornar el workspace_id del recurso
    como primer valor de retorno, o None si no pertenece al workspace.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Por favor inicia sesión', 'warning')
            return redirect(url_for('login'))

        # Ejecutar la función original
        result = f(*args, **kwargs)

        # Si la función retorna una tupla (workspace_id, response)
        if isinstance(result, tuple) and len(result) == 2:
            resource_workspace_id, response = result

            if resource_workspace_id != current_user.workspace_id:
                flash('Acceso denegado a recurso de otro workspace', 'danger')
                abort(403)

            return response

        return result

    return decorated_function
