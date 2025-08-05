"""
Enterprise Security framework for TQ GenAI Chat application.
Provides SSO integration, RBAC, compliance features, and advanced security controls.
"""

import base64
import hmac
import json
import logging
import secrets
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    import ldap3

    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"
    SERVICE_ACCOUNT = "service_account"


class Permission(Enum):
    """System permissions."""

    # Chat permissions
    CHAT_CREATE = "chat:create"
    CHAT_READ = "chat:read"
    CHAT_UPDATE = "chat:update"
    CHAT_DELETE = "chat:delete"
    CHAT_EXPORT = "chat:export"

    # File permissions
    FILE_UPLOAD = "file:upload"
    FILE_DOWNLOAD = "file:download"
    FILE_DELETE = "file:delete"
    FILE_SHARE = "file:share"

    # Admin permissions
    USER_MANAGE = "user:manage"
    SYSTEM_CONFIG = "system:config"
    AUDIT_VIEW = "audit:view"
    METRICS_VIEW = "metrics:view"

    # API permissions
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_ADMIN = "api:admin"


class ComplianceStandard(Enum):
    """Compliance standards."""

    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    PCI_DSS = "pci_dss"


@dataclass
class User:
    """User entity with security attributes."""

    id: str
    username: str
    email: str
    roles: set[UserRole] = field(default_factory=set)
    permissions: set[Permission] = field(default_factory=set)
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: datetime | None = None
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    password_hash: str | None = None
    mfa_enabled: bool = False
    mfa_secret: str | None = None
    session_timeout: int = 3600  # seconds
    requires_password_change: bool = False

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions

    def has_role(self, role: UserRole) -> bool:
        """Check if user has specific role."""
        return role in self.roles

    def is_locked(self) -> bool:
        """Check if account is locked."""
        return self.locked_until and self.locked_until > datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "roles": [role.value for role in self.roles],
            "permissions": [perm.value for perm in self.permissions],
            "attributes": self.attributes,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "mfa_enabled": self.mfa_enabled,
            "requires_password_change": self.requires_password_change,
        }


@dataclass
class SecurityEvent:
    """Security audit event."""

    id: str
    event_type: str
    user_id: str
    username: str
    ip_address: str
    user_agent: str
    resource: str
    action: str
    result: str  # success, failure, blocked
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)
    risk_score: int = 0  # 0-100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "username": self.username,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource": self.resource,
            "action": self.action,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "risk_score": self.risk_score,
        }


class CryptographyManager:
    """Handles encryption, decryption, and key management."""

    def __init__(self, master_key: str | None = None):
        self.master_key = master_key or self._generate_master_key()
        self.fernet = Fernet(self.master_key.encode())

        # Generate RSA key pair for asymmetric encryption
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()

    def _generate_master_key(self) -> str:
        """Generate a new master key."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

    def encrypt_data(self, data: str) -> str:
        """Encrypt data using symmetric encryption."""
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data using symmetric encryption."""
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def encrypt_with_public_key(self, data: str, public_key_pem: str | None = None) -> str:
        """Encrypt data with RSA public key."""
        try:
            if public_key_pem:
                public_key = serialization.load_pem_public_key(public_key_pem.encode())
            else:
                public_key = self.public_key

            encrypted = public_key.encrypt(
                data.encode(),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"RSA encryption failed: {e}")
            raise

    def decrypt_with_private_key(self, encrypted_data: str) -> str:
        """Decrypt data with RSA private key."""
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.private_key.decrypt(
                decoded,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            return decrypted.decode()
        except Exception as e:
            logger.error(f"RSA decryption failed: {e}")
            raise

    def hash_password(self, password: str, salt: str | None = None) -> tuple[str, str]:
        """Hash password with salt using PBKDF2."""
        if salt is None:
            salt = secrets.token_urlsafe(32)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=salt.encode(), iterations=100000
        )

        key = kdf.derive(password.encode())
        password_hash = base64.urlsafe_b64encode(key).decode()

        return password_hash, salt

    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against hash."""
        try:
            computed_hash, _ = self.hash_password(password, salt)
            return hmac.compare_digest(computed_hash, password_hash)
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)

    def get_public_key_pem(self) -> str:
        """Get public key in PEM format."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()


class AuthenticationProvider(ABC):
    """Abstract authentication provider interface."""

    @abstractmethod
    async def authenticate(self, username: str, password: str) -> User | None:
        """Authenticate user credentials."""
        pass

    @abstractmethod
    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID."""
        pass

    @abstractmethod
    async def create_user(self, user: User, password: str) -> bool:
        """Create new user."""
        pass

    @abstractmethod
    async def update_user(self, user: User) -> bool:
        """Update existing user."""
        pass


class LocalAuthenticationProvider(AuthenticationProvider):
    """Local authentication using database storage."""

    def __init__(self, crypto_manager: CryptographyManager):
        self.crypto = crypto_manager
        self.users: dict[str, User] = {}
        self.password_data: dict[str, tuple[str, str]] = {}  # user_id -> (hash, salt)

        # Create default admin user
        self._create_default_admin()

    def _create_default_admin(self):
        """Create default admin user."""
        admin_user = User(
            id=str(uuid.uuid4()),
            username="admin",
            email="admin@example.com",
            roles={UserRole.ADMIN},
            permissions=set(Permission),  # All permissions
        )

        password_hash, salt = self.crypto.hash_password("admin123")

        self.users[admin_user.id] = admin_user
        self.password_data[admin_user.id] = (password_hash, salt)

    async def authenticate(self, username: str, password: str) -> User | None:
        """Authenticate user credentials."""
        for user in self.users.values():
            if user.username == username:
                if user.is_locked():
                    logger.warning(f"Authentication attempt for locked user: {username}")
                    return None

                if user.id in self.password_data:
                    password_hash, salt = self.password_data[user.id]

                    if self.crypto.verify_password(password, password_hash, salt):
                        user.last_login = datetime.utcnow()
                        user.failed_login_attempts = 0
                        return user
                    else:
                        user.failed_login_attempts += 1

                        # Lock account after 5 failed attempts
                        if user.failed_login_attempts >= 5:
                            user.locked_until = datetime.utcnow() + timedelta(minutes=30)

                        return None

        return None

    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID."""
        return self.users.get(user_id)

    async def create_user(self, user: User, password: str) -> bool:
        """Create new user."""
        try:
            password_hash, salt = self.crypto.hash_password(password)

            self.users[user.id] = user
            self.password_data[user.id] = (password_hash, salt)

            return True
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False

    async def update_user(self, user: User) -> bool:
        """Update existing user."""
        if user.id in self.users:
            self.users[user.id] = user
            return True
        return False


class LDAPAuthenticationProvider(AuthenticationProvider):
    """LDAP/Active Directory authentication provider."""

    def __init__(
        self, ldap_server: str, base_dn: str, bind_dn: str = None, bind_password: str = None
    ):
        if not LDAP_AVAILABLE:
            raise ImportError("ldap3 package required for LDAP authentication")

        self.server = ldap3.Server(ldap_server)
        self.base_dn = base_dn
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.user_cache: dict[str, User] = {}

    async def authenticate(self, username: str, password: str) -> User | None:
        """Authenticate against LDAP."""
        try:
            # Bind with service account if provided
            if self.bind_dn:
                conn = ldap3.Connection(
                    self.server, self.bind_dn, self.bind_password, auto_bind=True
                )
            else:
                conn = ldap3.Connection(self.server, auto_bind=True)

            # Search for user
            search_filter = f"(sAMAccountName={username})"
            conn.search(self.base_dn, search_filter, attributes=["*"])

            if not conn.entries:
                return None

            user_entry = conn.entries[0]
            user_dn = user_entry.entry_dn

            # Try to bind with user credentials
            user_conn = ldap3.Connection(self.server, user_dn, password)

            if user_conn.bind():
                # Create user object from LDAP attributes
                user = User(
                    id=str(user_entry.objectGUID),
                    username=username,
                    email=str(user_entry.mail)
                    if hasattr(user_entry, "mail")
                    else f"{username}@company.com",
                    roles={UserRole.USER},  # Default role, could be mapped from LDAP groups
                    last_login=datetime.utcnow(),
                )

                # Map LDAP groups to roles
                if hasattr(user_entry, "memberOf"):
                    user.roles = self._map_ldap_groups_to_roles(user_entry.memberOf)

                # Set permissions based on roles
                user.permissions = self._get_permissions_for_roles(user.roles)

                self.user_cache[user.id] = user
                return user

            return None

        except Exception as e:
            logger.error(f"LDAP authentication failed: {e}")
            return None

    def _map_ldap_groups_to_roles(self, groups: list[str]) -> set[UserRole]:
        """Map LDAP groups to application roles."""
        roles = {UserRole.USER}  # Default role

        group_role_mapping = {
            "CN=TQ-GenAI-Admins": UserRole.ADMIN,
            "CN=TQ-GenAI-Managers": UserRole.MANAGER,
            "CN=Domain Admins": UserRole.ADMIN,
        }

        for group in groups:
            for group_dn, role in group_role_mapping.items():
                if group_dn in str(group):
                    roles.add(role)

        return roles

    def _get_permissions_for_roles(self, roles: set[UserRole]) -> set[Permission]:
        """Get permissions based on roles."""
        permissions = set()

        role_permissions = {
            UserRole.ADMIN: set(Permission),  # All permissions
            UserRole.MANAGER: {
                Permission.CHAT_CREATE,
                Permission.CHAT_READ,
                Permission.CHAT_UPDATE,
                Permission.CHAT_EXPORT,
                Permission.FILE_UPLOAD,
                Permission.FILE_DOWNLOAD,
                Permission.FILE_SHARE,
                Permission.METRICS_VIEW,
                Permission.API_READ,
                Permission.API_WRITE,
            },
            UserRole.USER: {
                Permission.CHAT_CREATE,
                Permission.CHAT_READ,
                Permission.CHAT_UPDATE,
                Permission.FILE_UPLOAD,
                Permission.FILE_DOWNLOAD,
                Permission.API_READ,
            },
            UserRole.GUEST: {Permission.CHAT_READ, Permission.FILE_DOWNLOAD},
        }

        for role in roles:
            if role in role_permissions:
                permissions.update(role_permissions[role])

        return permissions

    async def get_user(self, user_id: str) -> User | None:
        """Get user by ID."""
        return self.user_cache.get(user_id)

    async def create_user(self, user: User, password: str) -> bool:
        """Create user (not supported for LDAP)."""
        logger.warning("User creation not supported for LDAP provider")
        return False

    async def update_user(self, user: User) -> bool:
        """Update user in cache."""
        self.user_cache[user.id] = user
        return True


class SessionManager:
    """Manages user sessions with security features."""

    def __init__(self, secret_key: str, session_timeout: int = 3600, redis_client=None):
        self.secret_key = secret_key
        self.session_timeout = session_timeout
        self.redis_client = redis_client
        self.sessions: dict[str, dict[str, Any]] = {}  # Fallback to memory

    def create_session(self, user: User, ip_address: str, user_agent: str) -> str:
        """Create a new session."""
        session_id = secrets.token_urlsafe(32)

        session_data = {
            "user_id": user.id,
            "username": user.username,
            "roles": [role.value for role in user.roles],
            "permissions": [perm.value for perm in user.permissions],
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=self.session_timeout)).isoformat(),
        }

        # Store session
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"session:{session_id}", self.session_timeout, json.dumps(session_data)
                )
            except Exception as e:
                logger.error(f"Failed to store session in Redis: {e}")
                self.sessions[session_id] = session_data
        else:
            self.sessions[session_id] = session_data

        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session data."""
        try:
            if self.redis_client:
                session_data = self.redis_client.get(f"session:{session_id}")
                if session_data:
                    return json.loads(session_data)
            else:
                return self.sessions.get(session_id)
        except Exception as e:
            logger.error(f"Failed to get session: {e}")

        return None

    def update_session_activity(self, session_id: str) -> bool:
        """Update session last activity."""
        session_data = self.get_session(session_id)
        if not session_data:
            return False

        session_data["last_activity"] = datetime.utcnow().isoformat()

        try:
            if self.redis_client:
                self.redis_client.setex(
                    f"session:{session_id}", self.session_timeout, json.dumps(session_data)
                )
            else:
                self.sessions[session_id] = session_data
            return True
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            return False

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        try:
            if self.redis_client:
                self.redis_client.delete(f"session:{session_id}")
            else:
                self.sessions.pop(session_id, None)
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate session: {e}")
            return False

    def is_session_valid(self, session_id: str) -> bool:
        """Check if session is valid and not expired."""
        session_data = self.get_session(session_id)
        if not session_data:
            return False

        try:
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            return datetime.utcnow() < expires_at
        except Exception:
            return False


class SecurityAuditLogger:
    """Logs security events for compliance and monitoring."""

    def __init__(self, log_file: str = "security_audit.log"):
        self.log_file = log_file
        self.events: list[SecurityEvent] = []

        # Setup file logger
        self.logger = logging.getLogger("security_audit")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_event(self, event: SecurityEvent):
        """Log a security event."""
        try:
            # Store in memory
            self.events.append(event)

            # Log to file
            self.logger.info(json.dumps(event.to_dict()))

            # Alert on high-risk events
            if event.risk_score >= 80:
                self._handle_high_risk_event(event)

        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    def _handle_high_risk_event(self, event: SecurityEvent):
        """Handle high-risk security events."""
        logger.critical(f"HIGH RISK SECURITY EVENT: {event.event_type} - {event.details}")

        # Could integrate with alerting systems here
        # - Send email notification
        # - Trigger security incident response
        # - Block IP address
        # - Disable user account

    def get_events(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        event_type: str = None,
        user_id: str = None,
    ) -> list[SecurityEvent]:
        """Get filtered security events."""
        filtered_events = self.events

        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]

        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]

        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]

        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]

        return filtered_events

    def generate_compliance_report(
        self, standard: ComplianceStandard, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """Generate compliance report."""
        events = self.get_events(start_date, end_date)

        report = {
            "standard": standard.value,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_events": len(events),
            "event_breakdown": {},
            "security_metrics": {},
            "recommendations": [],
        }

        # Event breakdown
        for event in events:
            event_type = event.event_type
            if event_type not in report["event_breakdown"]:
                report["event_breakdown"][event_type] = 0
            report["event_breakdown"][event_type] += 1

        # Security metrics
        failed_logins = len(
            [e for e in events if e.event_type == "authentication" and e.result == "failure"]
        )
        successful_logins = len(
            [e for e in events if e.event_type == "authentication" and e.result == "success"]
        )
        high_risk_events = len([e for e in events if e.risk_score >= 80])

        report["security_metrics"] = {
            "failed_login_attempts": failed_logins,
            "successful_logins": successful_logins,
            "high_risk_events": high_risk_events,
            "login_failure_rate": failed_logins / (failed_logins + successful_logins)
            if (failed_logins + successful_logins) > 0
            else 0,
        }

        # Compliance-specific recommendations
        if standard == ComplianceStandard.GDPR:
            report["recommendations"].extend(self._get_gdpr_recommendations(events))
        elif standard == ComplianceStandard.SOC2:
            report["recommendations"].extend(self._get_soc2_recommendations(events))

        return report

    def _get_gdpr_recommendations(self, events: list[SecurityEvent]) -> list[str]:
        """Get GDPR-specific recommendations."""
        recommendations = []

        data_access_events = [e for e in events if "data_access" in e.event_type]
        if len(data_access_events) > 1000:
            recommendations.append(
                "High volume of data access events - review data minimization practices"
            )

        export_events = [e for e in events if "export" in e.event_type]
        if export_events:
            recommendations.append(
                "Data export events detected - ensure proper consent and purpose limitation"
            )

        return recommendations

    def _get_soc2_recommendations(self, events: list[SecurityEvent]) -> list[str]:
        """Get SOC2-specific recommendations."""
        recommendations = []

        admin_events = [e for e in events if "admin" in e.event_type]
        if admin_events:
            recommendations.append(
                "Administrative activities detected - ensure proper segregation of duties"
            )

        failed_auth_events = [
            e for e in events if e.event_type == "authentication" and e.result == "failure"
        ]
        if len(failed_auth_events) > 100:
            recommendations.append(
                "High number of authentication failures - consider implementing stronger access controls"
            )

        return recommendations


class EnterpriseSecurityManager:
    """Main enterprise security manager orchestrating all security components."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

        # Initialize crypto manager
        self.crypto = CryptographyManager(config.get("master_key"))

        # Initialize authentication provider
        auth_type = config.get("auth_type", "local")
        if auth_type == "ldap":
            self.auth_provider = LDAPAuthenticationProvider(
                ldap_server=config["ldap_server"],
                base_dn=config["ldap_base_dn"],
                bind_dn=config.get("ldap_bind_dn"),
                bind_password=config.get("ldap_bind_password"),
            )
        else:
            self.auth_provider = LocalAuthenticationProvider(self.crypto)

        # Initialize session manager
        redis_client = None
        if REDIS_AVAILABLE and config.get("redis_url"):
            try:
                redis_client = redis.from_url(config["redis_url"])
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")

        self.session_manager = SessionManager(
            secret_key=config.get("secret_key", "default-secret"),
            session_timeout=config.get("session_timeout", 3600),
            redis_client=redis_client,
        )

        # Initialize audit logger
        self.audit_logger = SecurityAuditLogger(
            log_file=config.get("audit_log_file", "security_audit.log")
        )

        # Security policies
        self.max_login_attempts = config.get("max_login_attempts", 5)
        self.password_min_length = config.get("password_min_length", 8)
        self.require_mfa = config.get("require_mfa", False)
        self.compliance_standards = set(
            ComplianceStandard(std) for std in config.get("compliance_standards", [])
        )

    async def authenticate_user(
        self, username: str, password: str, ip_address: str, user_agent: str
    ) -> tuple[str | None, User | None]:
        """Authenticate user and create session."""
        # Log authentication attempt
        event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type="authentication",
            user_id="unknown",
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            resource="auth",
            action="login",
            result="attempt",
        )

        try:
            user = await self.auth_provider.authenticate(username, password)

            if user:
                # Successful authentication
                session_id = self.session_manager.create_session(user, ip_address, user_agent)

                event.user_id = user.id
                event.result = "success"
                event.details = {"session_id": session_id}
                self.audit_logger.log_event(event)

                return session_id, user
            else:
                # Failed authentication
                event.result = "failure"
                event.risk_score = 50
                self.audit_logger.log_event(event)

                return None, None

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            event.result = "error"
            event.risk_score = 70
            event.details = {"error": str(e)}
            self.audit_logger.log_event(event)

            return None, None

    def validate_session(self, session_id: str) -> User | None:
        """Validate session and return user."""
        if not self.session_manager.is_session_valid(session_id):
            return None

        session_data = self.session_manager.get_session(session_id)
        if not session_data:
            return None

        # Update session activity
        self.session_manager.update_session_activity(session_id)

        # Reconstruct user object
        user = User(
            id=session_data["user_id"],
            username=session_data["username"],
            email="",  # Could be stored in session if needed
            roles={UserRole(role) for role in session_data["roles"]},
            permissions={Permission(perm) for perm in session_data["permissions"]},
        )

        return user

    def logout_user(self, session_id: str, user_id: str, ip_address: str, user_agent: str):
        """Logout user and invalidate session."""
        success = self.session_manager.invalidate_session(session_id)

        # Log logout event
        event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type="authentication",
            user_id=user_id,
            username="",
            ip_address=ip_address,
            user_agent=user_agent,
            resource="auth",
            action="logout",
            result="success" if success else "failure",
        )
        self.audit_logger.log_event(event)

    def check_permission(
        self, user: User, permission: Permission, resource: str, ip_address: str, user_agent: str
    ) -> bool:
        """Check if user has permission for action."""
        has_permission = user.has_permission(permission)

        # Log access attempt
        event = SecurityEvent(
            id=str(uuid.uuid4()),
            event_type="authorization",
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            resource=resource,
            action=permission.value,
            result="success" if has_permission else "denied",
            details={"requested_permission": permission.value},
        )

        if not has_permission:
            event.risk_score = 30

        self.audit_logger.log_event(event)

        return has_permission

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.crypto.encrypt_data(data)

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self.crypto.decrypt_data(encrypted_data)

    def generate_compliance_report(
        self, standard: ComplianceStandard, days: int = 30
    ) -> dict[str, Any]:
        """Generate compliance report."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        return self.audit_logger.generate_compliance_report(standard, start_date, end_date)

    def get_security_metrics(self) -> dict[str, Any]:
        """Get security metrics dashboard."""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        events_24h = self.audit_logger.get_events(start_time=last_24h)
        events_7d = self.audit_logger.get_events(start_time=last_7d)

        return {
            "last_24_hours": {
                "total_events": len(events_24h),
                "failed_logins": len(
                    [
                        e
                        for e in events_24h
                        if e.event_type == "authentication" and e.result == "failure"
                    ]
                ),
                "high_risk_events": len([e for e in events_24h if e.risk_score >= 80]),
            },
            "last_7_days": {
                "total_events": len(events_7d),
                "unique_users": len(set(e.user_id for e in events_7d)),
                "authorization_denials": len(
                    [
                        e
                        for e in events_7d
                        if e.event_type == "authorization" and e.result == "denied"
                    ]
                ),
            },
            "compliance_status": {
                "enabled_standards": [std.value for std in self.compliance_standards],
                "audit_log_entries": len(self.audit_logger.events),
            },
        }


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def main():
        # Configuration
        config = {
            "auth_type": "local",  # or 'ldap'
            "secret_key": "your-secret-key-here",
            "session_timeout": 3600,
            "max_login_attempts": 5,
            "compliance_standards": ["gdpr", "soc2"],
        }

        # Initialize security manager
        security_manager = EnterpriseSecurityManager(config)

        # Test authentication with hardcoded test values  # nosec B106
        session_id, user = await security_manager.authenticate_user(
            username="testuser",
            password="testpass123",  # nosec B106
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
        )

        if session_id and user:
            print(f"Authentication successful. Session: {session_id}")
            print(f"User: {user.username}, Roles: {[r.value for r in user.roles]}")

            # Test permission check
            has_perm = security_manager.check_permission(
                user=user,
                permission=Permission.CHAT_CREATE,
                resource="/api/chat",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
            )
            print(f"Can create chat: {has_perm}")

            # Test data encryption
            sensitive_data = "This is sensitive information"
            encrypted = security_manager.encrypt_sensitive_data(sensitive_data)
            decrypted = security_manager.decrypt_sensitive_data(encrypted)
            print(f"Encryption test: {decrypted == sensitive_data}")

            # Get security metrics
            metrics = security_manager.get_security_metrics()
            print("Security metrics:", json.dumps(metrics, indent=2))

            # Generate compliance report
            report = security_manager.generate_compliance_report(ComplianceStandard.SOC2)
            print("Compliance report:", json.dumps(report, indent=2, default=str))

        else:
            print("Authentication failed")

    asyncio.run(main())
