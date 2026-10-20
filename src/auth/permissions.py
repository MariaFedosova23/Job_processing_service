ROLE_SCOPES = {
    'admin': [
        'users:create',
        'users:get',
        'users:update',
        'users:is_active_false',
        'passwords:reset',
        'tasks:create',
        'tasks:read',
        'tasks:run',
        'tasks:retry',
        'tasks:cancel',
        'tasks:delete'
    ],
    'operator': [
        'tasks:create',
        'tasks:read_own',
        'tasks:run_own',
        'tasks:retry_own',
        'tasks:cancel_own',
        'tasks:delete_own'
    ],
    'viewer': [
        'tasks:read_own'
    ]
}

def get_scopes_for_role(role: str) -> list[str]:
    """
    Возвращает список скоупов, есть ли роль есть, иначе пустой список.
    """
    return ROLE_SCOPES.get(role, [])