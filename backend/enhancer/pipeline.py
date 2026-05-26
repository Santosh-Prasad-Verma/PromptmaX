from .utils.email import send_welcome_email


def send_welcome_email_pipeline(backend, user, response, is_new=False, *args, **kwargs):
    if is_new and user.email:
        name = user.first_name or user.username
        if not name:
            name = response.get('name') or response.get('given_name') or 'Operator'
        send_welcome_email(user.email, name)
    return None
