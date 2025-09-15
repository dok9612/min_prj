from commands import COMMANDS
from autocomplete import find_longest_common_prefix

def main():
    print("Welcome to the Micro Game Engine CLI.")
    print("Type a command prefix and hit Enter to see suggestions.")
    print("Available command families: spawn, set, get, quit")
    print("-" * 20)

    current_input = ""
    while True:
        prompt = f"> {current_input}"
        user_keystroke = input(prompt)
        
        current_input = current_input + user_keystroke
        
        if current_input == "quit":
            print("Exiting")
            break
        
        matches = [cmd for cmd in COMMANDS if cmd.startswith(current_input)]
        
        if not matches:
            print("  -> No commands match. Try again.")
            current_input = ""
        elif len(matches) == 1:
            complete_cmd = matches[0]
            print(f"  -> Autocompleted to: {complete_cmd}")
            current_input = ""
        else:
            prefix = find_longest_common_prefix(matches)
            print(f"  -> Multiple possibilities: {matches}")
            print(f"  -> Common prefix: {prefix}")
            current_input = prefix

if __name__ == "__main__":
    main()