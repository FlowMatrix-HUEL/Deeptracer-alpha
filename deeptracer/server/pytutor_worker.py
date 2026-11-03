from __future__ import annotations

import json
import sys
import types
from contextlib import redirect_stdout
from io import StringIO

from deeptracer.server.pytutor_service import get_pytutor_static_dir


def main() -> None:
    payload = json.load(sys.stdin)
    vendor_path = str(get_pytutor_static_dir())
    if vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)

    if "imp" not in sys.modules:
        imp_module = types.ModuleType("imp")
        imp_module.new_module = types.ModuleType
        sys.modules["imp"] = imp_module

    import pg_logger  # type: ignore

    output = StringIO()

    def finalizer(input_code: str, output_trace: list[dict]) -> None:
        json.dump(
            {"code": input_code, "trace": output_trace},
            output,
            ensure_ascii=False,
        )

    with redirect_stdout(StringIO()):
        pg_logger.exec_script_str_local(
            payload.get("userScript", ""),
            payload.get("rawInputJson", "[]"),
            bool(payload.get("cumulativeMode", False)),
            bool(payload.get("heapPrimitives", False)),
            finalizer,
        )
    sys.__stdout__.write(output.getvalue())
    sys.__stdout__.flush()


if __name__ == "__main__":
    main()
