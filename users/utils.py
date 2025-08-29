def get_client_ip(request):
    """
    Get the client's IP address from the request.
    Handles various HTTP headers to get the real IP behind proxies.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get the first IP in the list (client IP, not proxy)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
