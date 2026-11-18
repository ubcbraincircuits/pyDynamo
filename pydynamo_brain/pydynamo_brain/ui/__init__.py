def __getattr__(name):
    if name == "DynamoWindow":
        from .dynamoWindow import DynamoWindow
        return DynamoWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
