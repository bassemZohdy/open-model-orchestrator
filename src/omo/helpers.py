import re
from decimal import Decimal, DecimalException, Inexact, localcontext

from omo.contracts import Arithmetic, ChatRequest, Result


def arithmetic(call: Arithmetic) -> Result:
    """Decimal strings retain precision; additive units are never inferred."""
    if call.unit and call.operation in {"multiply", "divide"}:
        return Result(status="unsupported", diagnostic="compound units require an explicit schema")
    try:
        with localcontext() as ctx:
            ctx.prec = 40
            a, b = Decimal(call.a), Decimal(call.b)
            match call.operation:
                case "add":
                    value = a + b
                case "subtract":
                    value = a - b
                case "multiply":
                    value = a * b
                case "divide":
                    if not b:
                        return Result(status="execution-error", diagnostic="division by zero")
                    value = a / b
            if not value.is_finite() or abs(value) > Decimal("1e24"):
                return Result(status="resource-limit", diagnostic="numeric range exceeded")
            if ctx.flags[Inexact]:
                return Result(
                    status="unsupported",
                    diagnostic="non-terminating decimal; specify rounding in a future API",
                )
            return Result(status="success", value={"value": format(value, "f"), "unit": call.unit})
    except DecimalException:
        return Result(status="execution-error", diagnostic="invalid decimal operation")


def fast_helper(request: ChatRequest) -> Arithmetic | None:
    # A documented full-command grammar, only in a single user turn. Quoted,
    # negated or context-dependent text does not enter this fast path.
    if len(request.messages) != 1:
        return None
    match = re.fullmatch(
        r"calc (-?\d{1,12}(?:\.\d{1,8})?) ([+*/-]) (-?\d{1,12}(?:\.\d{1,8})?)",
        request.messages[0].content,
    )
    if not match:
        return None
    a, op, b = match.groups()
    return Arithmetic.model_validate(
        {
            "operation": {"+": "add", "-": "subtract", "*": "multiply", "/": "divide"}[op],
            "a": a,
            "b": b,
        }
    )
