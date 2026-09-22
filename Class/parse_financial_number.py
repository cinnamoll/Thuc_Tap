def parse_number(val):
    if val is None:
        return None
        
    t = str(val).strip()
    if not t or t in ("-", "—", "–"):
        return None
        
    is_neg = False
    if t.startswith("(") and t.endswith(")"):
        is_neg = True
        t = t[1:-1]
    elif t.startswith("-") or t.startswith("–"):
        is_neg = True
        t = t[1:]

    t = t.replace(" ", "")
    if t.count(".") > 1 and "," not in t:
        t = t.replace(".", "")
    elif t.count(",") > 1 and "." not in t:
        t = t.replace(",", "")
    elif "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t and "." not in t:
        parts = t.split(",")
        if len(parts[-1]) == 3:
            t = t.replace(",", "")
        else:
            t = t.replace(",", ".")
    elif "." in t and "," not in t:
        parts = t.split(".")
        if len(parts[-1]) == 3 and all(len(p) <= 3 for p in parts[:-1]):
            t = t.replace(".", "")

    try:
        val = int(t)
        return -val if is_neg else val
    except ValueError:
        try:
            fval = float(t)
            return -fval if is_neg else fval
        except ValueError:
            return None