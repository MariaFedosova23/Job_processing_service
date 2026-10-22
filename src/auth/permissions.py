ROLE_SCOPES = {
    'admin': [
        'users:create',
        'users:get',
        'users:update',
        'users:is_active_false',
        'passwords:reset',
        'tasks:create',
        'tasks:patch_status',
        'tasks:read',
        'tasks:process',
        'tasks:retry',
        'tasks:cancel',
        'tasks:delete',
        'tasks:upload_file'

    ],
    'operator': [
        'tasks:create',
        'tasks:patch_own_status',
        'tasks:read_own',
        'tasks:process_own',
        'tasks:retry_own',
        'tasks:cancel_own',
        'tasks:delete_own',
        'tasks:upload_file_own'
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