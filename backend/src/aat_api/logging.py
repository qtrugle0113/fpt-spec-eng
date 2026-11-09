"""Structured safe diagnostics; no exception payload, path or credential logging."""
import logging
import re


def redact(value):
    text=str(value)
    text=re.sub(r'(?i)(postgres(?:ql)?|mysql)://\S+','[REDACTED_DSN]',text)
    text=re.sub(r'(?i)(password|token|secret|ciphertext)\s*[=:]\s*\S+',r'\1=[REDACTED]',text)
    text=re.sub(r'(?i)(?:/secrets/|[A-Z]:\\)[^\s]*','[REDACTED_PATH]',text)
    return text


logger=logging.getLogger('aat.safe')


def log_failure(request_id,exc):
    # Only controlled class and generated identity, never str(exc)/traceback.
    logger.error('request_failed request_id=%s exception_type=%s',request_id,type(exc).__name__)
