def name_has(name, *tokens):
    value = (name or "").lower()
    return any(token in value for token in tokens)


def edge_member(span_ratio, center_ratio):
    return span_ratio <= 0.42 and center_ratio >= 0.32


def generic_rule(span_ratio, center_ratio):
    if span_ratio >= 0.62:
        return "STRETCH"
    if span_ratio <= 0.38 and center_ratio >= 0.34:
        return "MOVE"
    return "FIXED"
