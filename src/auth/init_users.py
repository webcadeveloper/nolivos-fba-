"""
Script para inicializar el sistema de usuarios.

Uso:
    python -m src.auth.init_users

Crea:
- Base de datos users.db
- Primer workspace
- Usuario owner inicial
"""

import sys
import os
from getpass import getpass

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.auth.user_manager import UserManager


def init_first_workspace():
    """Inicializa el primer workspace y usuario owner"""

    print("=" * 60)
    print("🚀 NOLIVOS FBA - Inicialización de Sistema Multi-Usuario")
    print("=" * 60)
    print()

    # Crear UserManager (esto inicializa la base de datos)
    user_manager = UserManager()

    print("✅ Base de datos inicializada (users.db)")
    print()

    # Solicitar datos del primer workspace
    print("📋 Configuración del Workspace Principal")
    print("-" * 60)

    workspace_name = input("Nombre del workspace (ej: 'Mi Empresa FBA'): ").strip()
    if not workspace_name:
        workspace_name = "Default Workspace"

    print()
    print("👤 Configuración del Usuario Owner")
    print("-" * 60)

    owner_email = input("Email del owner: ").strip()
    while not owner_email or '@' not in owner_email:
        print("❌ Email inválido")
        owner_email = input("Email del owner: ").strip()

    owner_password = getpass("Contraseña del owner: ")
    while len(owner_password) < 6:
        print("❌ La contraseña debe tener al menos 6 caracteres")
        owner_password = getpass("Contraseña del owner: ")

    owner_password_confirm = getpass("Confirmar contraseña: ")
    while owner_password != owner_password_confirm:
        print("❌ Las contraseñas no coinciden")
        owner_password = getpass("Contraseña del owner: ")
        owner_password_confirm = getpass("Confirmar contraseña: ")

    # Crear workspace y owner
    print()
    print("🔨 Creando workspace y usuario...")

    workspace_id = user_manager.create_workspace(
        name=workspace_name,
        owner_email=owner_email,
        owner_password=owner_password
    )

    if workspace_id:
        print()
        print("=" * 60)
        print("✅ ¡SISTEMA INICIALIZADO CORRECTAMENTE!")
        print("=" * 60)
        print()
        print(f"📦 Workspace ID: {workspace_id}")
        print(f"📦 Workspace Name: {workspace_name}")
        print(f"👤 Owner Email: {owner_email}")
        print(f"🔑 Role: owner (acceso completo)")
        print()
        print("🌐 Ahora puedes iniciar sesión en la aplicación web:")
        print("   python app.py")
        print()
        print("📚 Para crear más usuarios:")
        print("   1. Inicia sesión como owner")
        print("   2. Ve a /users")
        print("   3. Invita nuevos usuarios con roles específicos")
        print()
        print("🎯 Roles disponibles:")
        print("   - owner:   Acceso completo, gestión de usuarios")
        print("   - analyst: Análisis completo, scans, reportes, webhooks")
        print("   - va:      Asistente virtual, dashboards básicos")
        print("   - viewer:  Solo lectura")
        print()
    else:
        print()
        print("=" * 60)
        print("❌ ERROR al crear workspace")
        print("=" * 60)
        print()
        print("Posibles causas:")
        print("- El email ya existe en la base de datos")
        print("- El nombre del workspace ya existe")
        print()
        print("Solución: Usa un email o nombre de workspace diferente")
        print()


def add_user_to_workspace():
    """Añade un usuario a un workspace existente (para uso por CLI)"""

    user_manager = UserManager()

    print()
    print("=" * 60)
    print("➕ Agregar Usuario a Workspace Existente")
    print("=" * 60)
    print()

    workspace_id = input("Workspace ID: ").strip()
    try:
        workspace_id = int(workspace_id)
    except ValueError:
        print("❌ Workspace ID debe ser un número")
        return

    # Verificar que el workspace existe
    workspace_info = user_manager.get_workspace_info(workspace_id)
    if not workspace_info:
        print(f"❌ Workspace {workspace_id} no existe")
        return

    print(f"✅ Workspace encontrado: {workspace_info['name']}")
    print()

    email = input("Email del nuevo usuario: ").strip()
    password = getpass("Contraseña: ")

    print()
    print("🎯 Selecciona el rol:")
    print("1. analyst - Análisis completo, scans, reportes, webhooks")
    print("2. va - Asistente virtual, dashboards básicos")
    print("3. viewer - Solo lectura")
    print("4. owner - Acceso completo (usar con precaución)")

    role_choice = input("Selecciona rol (1-4): ").strip()
    role_map = {
        '1': 'analyst',
        '2': 'va',
        '3': 'viewer',
        '4': 'owner'
    }

    role = role_map.get(role_choice, 'viewer')

    user_id = user_manager.create_user(email, password, role, workspace_id)

    if user_id:
        print()
        print(f"✅ Usuario creado exitosamente!")
        print(f"   User ID: {user_id}")
        print(f"   Email: {email}")
        print(f"   Role: {role}")
        print(f"   Workspace: {workspace_info['name']}")
        print()
    else:
        print()
        print("❌ Error creando usuario (el email ya existe)")
        print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--add-user":
        add_user_to_workspace()
    else:
        init_first_workspace()
