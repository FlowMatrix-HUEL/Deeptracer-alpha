import code
import os
import sys
import io

def SetInteract(namespace: dict,
                func_name:str,
                event:str,
                arg_text:str|None = None,
                returned:str|None = None
                ):
    stdin_fd = os.dup(0)
    banner = "\n==== Tracer Interactive Shell ====\n"
    if event == "call":
        showed = f"\n===+{func_name}({arg_text})+===\n"
    elif event == "return":
        showed = f"\n===+{func_name} returned {returned}====\n"
    try:
        code.interact(local=namespace, banner=banner+showed)
    except (SystemExit, EOFError, ValueError) as e:
        print(f"\n[Tracer] Interactive exit: {type(e).__name__}")
    finally:
        sys.stdin = io.TextIOWrapper(
            io.BufferedReader(io.FileIO(stdin_fd, 'rb', closefd=False)),
            encoding='utf-8'
        )
        os.close(stdin_fd)