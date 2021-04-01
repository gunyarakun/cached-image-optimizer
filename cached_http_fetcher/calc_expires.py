from requests.structures import CaseInsensitiveDict

# Ref.) https://tools.ietf.org/html/rfc7234#section-5.2
CACHE_CONTROL_DIRECTIVES = {
    "max-age": (int, True),
    "max-stale": (int, False),
    "min-fresh": (int, True),
    "no-cache": (None, False),
    "no-store": (None, False),
    "no-transform": (None, False),
    "only-if-cached": (None, False),
    "must-revalidate": (None, False),
    "public": (None, False),
    "private": (None, False),
    "proxy-revalidate": (None, False),
    "s-maxage": (int, True),
}

def parse_cache_control(headers: CaseInsensitiveDict):
    cache_control = headers.get("cache-control", "")

    directives = {}

    for part in cache_control.split(","):
        part = part.strip()
        if not part:
            continue

        s = part.split("=", 1)
        key = s[0].strip()

        try:
            value_type, must_have_value = CACHE_CONTROL_DIRECTIVES[key]
        except KeyError:
            continue

        if not value_type or not must_have_value:
            directives[key] = None
        if value_type:
            try:
                directives[key] = value_type(s[1].strip())
            except IndexError:
                pass
            except ValueError:
                pass

    return directives
