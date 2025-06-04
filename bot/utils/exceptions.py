"""
Custom Exception Hierarchy
Standardized exceptions for better error handling
"""

class EmeraldBotException(Exception):
    """Base exception for Emerald bot"""
    pass

class DatabaseException(EmeraldBotException):
    """Database-related exceptions"""
    pass

class PremiumException(EmeraldBotException):
    """Premium feature access exceptions"""
    pass

class ValidationException(EmeraldBotException):
    """Input validation exceptions"""
    pass

class ParserException(EmeraldBotException):
    """Log parser exceptions"""
    pass

class ConfigurationException(EmeraldBotException):
    """Configuration-related exceptions"""
    pass

class RateLimitException(EmeraldBotException):
    """Rate limiting exceptions"""
    pass
