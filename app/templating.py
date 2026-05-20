import json

from fastapi.templating import Jinja2Templates
from markupsafe import Markup

templates = Jinja2Templates(directory="templates")
templates.env.filters["tojson"] = lambda value: Markup(json.dumps(value, default=str))
