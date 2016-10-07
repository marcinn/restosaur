def response_content_as_text(response):
    if isinstance(response.content, bytes):
        return response.content.decode(response.charset)
