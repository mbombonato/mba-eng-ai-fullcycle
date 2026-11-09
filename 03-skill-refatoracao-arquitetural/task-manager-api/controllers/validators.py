"""Validação de entrada única por recurso (mesmas regras em create e update)."""
import re
from datetime import datetime

from config.constants import (
    DATE_FORMAT, DEFAULT_CATEGORY_COLOR, DEFAULT_PRIORITY, DEFAULT_ROLE, MAX_PRIORITY, MAX_TITLE_LENGTH,
    MIN_PASSWORD_LENGTH, MIN_PRIORITY, MIN_TITLE_LENGTH, TASK_STATUS_PENDING, TASK_STATUSES, USER_ROLES,
)
from middlewares.error_handler import ValidationError

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')
COLOR_REGEX = re.compile(r'^#[0-9a-fA-F]{6}$')


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def require_body(data):
    if not isinstance(data, dict) or not data:
        raise ValidationError('Dados inválidos')
    return data


def parse_int_arg(value, name):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValidationError(f'Parâmetro {name} inválido') from exc


# ---------------------------------------------------------------- tasks

def _validate_title(title):
    if not title:
        raise ValidationError('Título é obrigatório')
    if not isinstance(title, str):
        raise ValidationError('Título deve ser texto')
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')
    return title


def _validate_priority(priority):
    if not _is_int(priority) or not MIN_PRIORITY <= priority <= MAX_PRIORITY:
        raise ValidationError(f'Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}')
    return priority


def _validate_due_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except (TypeError, ValueError) as exc:
        raise ValidationError('Formato de data inválido. Use YYYY-MM-DD') from exc


def _validate_tags(tags):
    if tags is None or tags == '':
        return None
    if isinstance(tags, list) and all(isinstance(t, str) for t in tags):
        return ','.join(tags)
    if isinstance(tags, str):
        return tags
    raise ValidationError('Tags devem ser uma lista de textos ou texto separado por vírgulas')


def _validate_ref(value, name):
    if value in (None, 0, ''):
        return None
    if not _is_int(value):
        raise ValidationError(f'{name} deve ser um número inteiro')
    return value


def validate_task(data, partial=False):
    """Retorna somente os campos presentes (partial=True) ou o payload completo com defaults."""
    data = require_body(data)
    fields = {}
    if not partial or 'title' in data:
        fields['title'] = _validate_title(data.get('title'))
    if not partial or 'description' in data:
        fields['description'] = data.get('description', '')
    if not partial or 'status' in data:
        status = data.get('status', TASK_STATUS_PENDING)
        if status not in TASK_STATUSES:
            raise ValidationError('Status inválido')
        fields['status'] = status
    if not partial or 'priority' in data:
        fields['priority'] = _validate_priority(data.get('priority', DEFAULT_PRIORITY))
    for key, label in (('user_id', 'user_id'), ('category_id', 'category_id')):
        if not partial or key in data:
            fields[key] = _validate_ref(data.get(key), label)
    if not partial or 'due_date' in data:
        fields['due_date'] = _validate_due_date(data.get('due_date'))
    if not partial or 'tags' in data:
        fields['tags'] = _validate_tags(data.get('tags'))
    return fields


# ---------------------------------------------------------------- users

def _validate_email(email):
    if not isinstance(email, str) or not EMAIL_REGEX.match(email):
        raise ValidationError('Email inválido')
    return email


def _validate_password(password, message):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(message)
    return password


def _validate_role(role):
    if role not in USER_ROLES:
        raise ValidationError('Role inválido')
    return role


def validate_new_user(data):
    data = require_body(data)
    for key, message in (('name', 'Nome é obrigatório'), ('email', 'Email é obrigatório'),
                         ('password', 'Senha é obrigatória')):
        if not data.get(key):
            raise ValidationError(message)
    return {
        'name': data['name'],
        'email': _validate_email(data['email']),
        'password': _validate_password(
            data['password'], f'Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres'),
        'role': _validate_role(data.get('role', DEFAULT_ROLE)),
    }


def validate_user_update(data):
    data = require_body(data)
    fields = {}
    if 'name' in data:
        if not isinstance(data['name'], str) or not data['name'].strip():
            raise ValidationError('Nome inválido')
        fields['name'] = data['name']
    if 'email' in data:
        fields['email'] = _validate_email(data['email'])
    if 'password' in data:
        fields['password'] = _validate_password(data['password'], 'Senha muito curta')
    if 'role' in data:
        fields['role'] = _validate_role(data['role'])
    if 'active' in data:
        if not isinstance(data['active'], bool):
            raise ValidationError('Campo active deve ser booleano')
        fields['active'] = data['active']
    return fields


def validate_login(data):
    data = require_body(data)
    email, password = data.get('email'), data.get('password')
    if not email or not password:
        raise ValidationError('Email e senha são obrigatórios')
    return email, password


# ---------------------------------------------------------------- categories

def validate_category(data, partial=False):
    data = require_body(data)
    fields = {}
    if not partial or 'name' in data:
        name = data.get('name')
        if not name or not isinstance(name, str):
            raise ValidationError('Nome é obrigatório')
        fields['name'] = name
    if not partial or 'description' in data:
        fields['description'] = data.get('description', '')
    if not partial or 'color' in data:
        color = data.get('color', DEFAULT_CATEGORY_COLOR)
        if not isinstance(color, str) or not COLOR_REGEX.match(color):
            raise ValidationError('Cor inválida. Use o formato #RRGGBB')
        fields['color'] = color
    return fields
