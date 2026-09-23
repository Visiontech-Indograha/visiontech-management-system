from app.core.discord import sanitize_for_discord


def test_sanitize_for_discord():
    text = "Error user with NIK 3201012345678901 and email test@example.com failed login."
    sanitized = sanitize_for_discord(text)
    
    assert "3201012345678901" not in sanitized
    assert "[NIK_MASKED]" in sanitized
    assert "test@example.com" not in sanitized
    assert "[EMAIL_MASKED]" in sanitized

def test_sanitize_phone():
    text = "Call +6281234567890 or 081234567890"
    sanitized = sanitize_for_discord(text)
    assert "+6281234567890" not in sanitized
    assert "081234567890" not in sanitized
    assert "[PHONE_MASKED]" in sanitized

def test_sanitize_jwt():
    text = "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c failed"
    sanitized = sanitize_for_discord(text)
    assert "eyJhbGciOiJI" not in sanitized
    assert "[JWT_MASKED]" in sanitized
