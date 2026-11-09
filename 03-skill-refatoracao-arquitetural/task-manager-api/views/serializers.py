"""Views/presenters: whitelist explícita dos campos de cada recurso (nunca expõe password)."""


def _fmt(value):
    return str(value) if value is not None else None


def task_view(task, *, overdue=None, with_relations=False):
    data = {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'user_id': task.user_id,
        'category_id': task.category_id,
        'created_at': str(task.created_at),
        'updated_at': str(task.updated_at),
        'due_date': _fmt(task.due_date),
        'tags': task.tag_list,
    }
    if overdue is not None:
        data['overdue'] = overdue
    if with_relations:
        data['user_name'] = task.user.name if task.user else None
        data['category_name'] = task.category.name if task.category else None
    return data


def task_summary_view(task, overdue):
    return {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'created_at': str(task.created_at),
        'due_date': _fmt(task.due_date),
        'overdue': overdue,
    }


def user_view(user):
    return {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role,
        'active': user.active,
        'created_at': str(user.created_at),
    }


def category_view(category):
    return {
        'id': category.id,
        'name': category.name,
        'description': category.description,
        'color': category.color,
        'created_at': str(category.created_at),
    }
