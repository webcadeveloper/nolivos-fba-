"""
Sistema de gestión de usuarios multi-tenant con roles y workspaces.

Roles disponibles:
- owner: Acceso completo, puede crear workspaces y usuarios
- analyst: Puede analizar productos, ver reportes, configurar webhooks
- va: Virtual Assistant - Solo puede ver dashboards y reportes básicos
- viewer: Solo lectura, no puede modificar nada

Features:
- Multi-tenant con workspaces aislados
- Role-Based Access Control (RBAC)
- Activity logging
- Password hashing con bcrypt
- Flask-Login integration
"""

import sqlite3
import hashlib
from datetime import datetime
from typing import Optional, List, Dict
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import os


class User(UserMixin):
    """Usuario con soporte Flask-Login"""

    def __init__(self, id: int, email: str, role: str, workspace_id: int,
                 workspace_name: str = None, created_at: str = None):
        self.id = id
        self.email = email
        self.role = role
        self.workspace_id = workspace_id
        self.workspace_name = workspace_name
        self.created_at = created_at

    def has_permission(self, permission: str) -> bool:
        """Verifica si el usuario tiene un permiso específico"""
        permissions_by_role = {
            'owner': ['*'],  # All permissions
            'analyst': [
                'view_dashboard', 'view_opportunities', 'view_reports',
                'scan_products', 'analyze_competitors', 'manage_webhooks',
                'export_data', 'view_api_keys', 'manage_alerts'
            ],
            'va': [
                'view_dashboard', 'view_opportunities', 'view_reports',
                'export_data'
            ],
            'viewer': [
                'view_dashboard', 'view_opportunities', 'view_reports'
            ]
        }

        role_permissions = permissions_by_role.get(self.role, [])
        return '*' in role_permissions or permission in role_permissions

    def can_manage_users(self) -> bool:
        """Solo owners pueden gestionar usuarios"""
        return self.role == 'owner'

    def can_edit_workspace(self) -> bool:
        """Solo owners pueden editar workspace settings"""
        return self.role == 'owner'

    def to_dict(self) -> Dict:
        """Convierte usuario a diccionario"""
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'workspace_id': self.workspace_id,
            'workspace_name': self.workspace_name,
            'created_at': self.created_at
        }


class UserManager:
    """Gestión de usuarios, workspaces y permisos"""

    # Roles válidos
    VALID_ROLES = ['owner', 'analyst', 'va', 'viewer']

    # Permisos por rol
    ROLE_PERMISSIONS = {
        'owner': 'Acceso completo - Gestión de usuarios y workspaces',
        'analyst': 'Análisis completo - Scans, reportes, webhooks, API',
        'va': 'Asistente virtual - Dashboards y reportes básicos',
        'viewer': 'Solo lectura - Ver dashboards y oportunidades'
    }

    def __init__(self, db_path: str = 'users.db'):
        """
        Inicializa el gestor de usuarios.

        Args:
            db_path: Ruta al archivo de base de datos SQLite
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Crea las tablas de usuarios, workspaces y activity log"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabla de workspaces (multi-tenant)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                owner_id INTEGER,
                created_at TEXT NOT NULL,
                settings TEXT,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        ''')

        # Tabla de usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                workspace_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
            )
        ''')

        # Tabla de activity log (auditoría)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                resource TEXT,
                details TEXT,
                ip_address TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # Índices para mejorar performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_workspace ON users(workspace_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_activity_user ON user_activity_log(user_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON user_activity_log(timestamp)
        ''')

        conn.commit()
        conn.close()

    def create_workspace(self, name: str, owner_email: str, owner_password: str) -> Optional[int]:
        """
        Crea un nuevo workspace con su usuario owner.

        Args:
            name: Nombre del workspace (ej: "Mi Empresa FBA")
            owner_email: Email del usuario owner
            owner_password: Contraseña del owner

        Returns:
            ID del workspace creado, o None si hay error
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Crear workspace
            cursor.execute('''
                INSERT INTO workspaces (name, created_at)
                VALUES (?, ?)
            ''', (name, datetime.now().isoformat()))

            workspace_id = cursor.lastrowid

            # Crear usuario owner
            password_hash = generate_password_hash(owner_password, method='pbkdf2:sha256')
            cursor.execute('''
                INSERT INTO users (email, password_hash, role, workspace_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (owner_email, password_hash, 'owner', workspace_id, datetime.now().isoformat()))

            owner_id = cursor.lastrowid

            # Actualizar workspace con owner_id
            cursor.execute('''
                UPDATE workspaces SET owner_id = ? WHERE id = ?
            ''', (owner_id, workspace_id))

            conn.commit()
            conn.close()

            return workspace_id

        except sqlite3.IntegrityError as e:
            print(f"Error creando workspace: {e}")
            return None

    def create_user(self, email: str, password: str, role: str, workspace_id: int) -> Optional[int]:
        """
        Crea un nuevo usuario en un workspace existente.

        Args:
            email: Email del usuario
            password: Contraseña en texto plano (se hasheará)
            role: Rol del usuario (owner, analyst, va, viewer)
            workspace_id: ID del workspace al que pertenece

        Returns:
            ID del usuario creado, o None si hay error
        """
        if role not in self.VALID_ROLES:
            print(f"Rol inválido: {role}. Roles válidos: {self.VALID_ROLES}")
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            password_hash = generate_password_hash(password, method='pbkdf2:sha256')

            cursor.execute('''
                INSERT INTO users (email, password_hash, role, workspace_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, password_hash, role, workspace_id, datetime.now().isoformat()))

            user_id = cursor.lastrowid

            conn.commit()
            conn.close()

            return user_id

        except sqlite3.IntegrityError:
            print(f"Usuario con email {email} ya existe")
            return None

    def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Autentica un usuario con email y password.

        Args:
            email: Email del usuario
            password: Contraseña en texto plano

        Returns:
            Objeto User si la autenticación es exitosa, None si falla
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT u.*, w.name as workspace_name
            FROM users u
            LEFT JOIN workspaces w ON u.workspace_id = w.id
            WHERE u.email = ? AND u.is_active = 1
        ''', (email,))

        row = cursor.fetchone()

        if row and check_password_hash(row['password_hash'], password):
            # Actualizar last_login
            cursor.execute('''
                UPDATE users SET last_login = ? WHERE id = ?
            ''', (datetime.now().isoformat(), row['id']))
            conn.commit()

            user = User(
                id=row['id'],
                email=row['email'],
                role=row['role'],
                workspace_id=row['workspace_id'],
                workspace_name=row['workspace_name'],
                created_at=row['created_at']
            )

            conn.close()
            return user

        conn.close()
        return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Obtiene un usuario por su ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT u.*, w.name as workspace_name
            FROM users u
            LEFT JOIN workspaces w ON u.workspace_id = w.id
            WHERE u.id = ?
        ''', (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return User(
                id=row['id'],
                email=row['email'],
                role=row['role'],
                workspace_id=row['workspace_id'],
                workspace_name=row['workspace_name'],
                created_at=row['created_at']
            )

        return None

    def get_users_by_workspace(self, workspace_id: int) -> List[Dict]:
        """Obtiene todos los usuarios de un workspace"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, email, role, created_at, last_login, is_active
            FROM users
            WHERE workspace_id = ?
            ORDER BY created_at ASC
        ''', (workspace_id,))

        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row['id'],
                'email': row['email'],
                'role': row['role'],
                'created_at': row['created_at'],
                'last_login': row['last_login'],
                'is_active': row['is_active'] == 1
            })

        conn.close()
        return users

    def change_role(self, user_id: int, new_role: str) -> bool:
        """Cambia el rol de un usuario"""
        if new_role not in self.VALID_ROLES:
            return False

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE users SET role = ? WHERE id = ?
            ''', (new_role, user_id))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Error cambiando rol: {e}")
            return False

    def deactivate_user(self, user_id: int) -> bool:
        """Desactiva un usuario (soft delete)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE users SET is_active = 0 WHERE id = ?
            ''', (user_id,))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Error desactivando usuario: {e}")
            return False

    def log_activity(self, user_id: int, action: str, resource: str = None,
                    details: str = None, ip_address: str = None):
        """
        Registra actividad de usuario para auditoría.

        Args:
            user_id: ID del usuario
            action: Acción realizada (ej: "login", "scan_products", "create_webhook")
            resource: Recurso afectado (ej: ASIN, webhook_id)
            details: Detalles adicionales en JSON
            ip_address: IP del usuario
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO user_activity_log
                (user_id, action, resource, details, ip_address, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, action, resource, details, ip_address, datetime.now().isoformat()))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Error logging activity: {e}")

    def get_user_activity(self, user_id: int, limit: int = 100) -> List[Dict]:
        """Obtiene el historial de actividad de un usuario"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT action, resource, details, ip_address, timestamp
            FROM user_activity_log
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))

        activities = []
        for row in cursor.fetchall():
            activities.append({
                'action': row['action'],
                'resource': row['resource'],
                'details': row['details'],
                'ip_address': row['ip_address'],
                'timestamp': row['timestamp']
            })

        conn.close()
        return activities

    def get_workspace_activity(self, workspace_id: int, limit: int = 100) -> List[Dict]:
        """Obtiene actividad de todos los usuarios de un workspace"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT u.email, l.action, l.resource, l.details, l.timestamp
            FROM user_activity_log l
            JOIN users u ON l.user_id = u.id
            WHERE u.workspace_id = ?
            ORDER BY l.timestamp DESC
            LIMIT ?
        ''', (workspace_id, limit))

        activities = []
        for row in cursor.fetchall():
            activities.append({
                'user_email': row['email'],
                'action': row['action'],
                'resource': row['resource'],
                'details': row['details'],
                'timestamp': row['timestamp']
            })

        conn.close()
        return activities

    def get_workspace_info(self, workspace_id: int) -> Optional[Dict]:
        """Obtiene información de un workspace"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT w.*, u.email as owner_email
            FROM workspaces w
            LEFT JOIN users u ON w.owner_id = u.id
            WHERE w.id = ?
        ''', (workspace_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row['id'],
                'name': row['name'],
                'owner_id': row['owner_id'],
                'owner_email': row['owner_email'],
                'created_at': row['created_at'],
                'settings': row['settings']
            }

        return None

    def change_password(self, user_id: int, new_password: str) -> bool:
        """Cambia la contraseña de un usuario"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')

            cursor.execute('''
                UPDATE users SET password_hash = ? WHERE id = ?
            ''', (password_hash, user_id))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Error cambiando contraseña: {e}")
            return False


# Singleton instance
user_manager = UserManager()
