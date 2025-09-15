"""
Combined script: Monitors the clipboard and automatically formats LaTeX/Markdown math expressions.
This version uses a robust, line-based parser for "Front:"/"Back:" formats, provides reliable,
slowed-down automation for Anki, and handles LaTeX tags and indentation.

Functionality:
1. Intelligently formats display math '$$...$$' and inline math '$...$'.
2. Handles '\tag{...}' by moving it to the end as a bold label.
3. Cleans up excessive blank lines.
4. Reliably parses flashcards from the clipboard using the specified "Front:"/"Back:" format.
5. Converts LaTeX delimiters to Anki-compatible \( \) and \[ \] during insertion.
6. Automates pasting into Anki via hotkey with enhanced reliability to prevent errors.

Dependencies:
- pyperclip (pip install pyperclip)
- pyautogui (pip install pyautogui)
- pynput (pip install pynput)
"""

import re
import time
import sys
import os
import pyperclip
import pyautogui
import threading
from pynput import keyboard as pynput_keyboard

# --- Global Variables ---
processing_cards_flag = False

# --- REGEX PATTERNS ---
PATTERN_DOUBLE = r"^(\s*)(.*?)(\$\$.*?\$\$)(.*)$"
PATTERN_SINGLE = r"\$([^$]*)\$"
PATTERN_TAG = r"\\tag\{(.*?)\}"


# --- HELPER FUNCTION FOR MATH CONTENT PROCESSING ---
def _process_math_content(content):
    """Handles \tag replacement and stripping whitespace from math content."""
    tag_suffix = ""
    tag_match = re.search(PATTERN_TAG, content)
    if tag_match:
        tag_label = tag_match.group(1)
        content = re.sub(PATTERN_TAG, "", content, count=1)
        tag_suffix = f" \\quad \\textbf{{({tag_label})}}"
    return content.strip() + tag_suffix


# --- REPLACER FUNCTIONS FOR re.sub ---
def format_display_math_block(match):
    """Reformats a display math block, preserving indentation."""
    indent, pre_text, dollar_block, post_text = match.groups()
    pre_text, post_text = pre_text.strip(), post_text.strip()

    content_match = re.search(r"\$\$\s*(.*?)\s*\$\$", dollar_block, re.DOTALL)
    if not content_match:
        return match.group(0)

    processed_content = _process_math_content(content_match.group(1))

    result = []
    if pre_text:
        result.append(indent + pre_text)
    result.extend([f"{indent}$$", f"{indent}{processed_content}", f"{indent}$$"])
    if post_text:
        result.append(indent + post_text)
    return "\n".join(result)


def format_inline_math(match):
    """Formats inline math content."""
    return f"${_process_math_content(match.group(1))}$"


# --- MAIN FORMATTING FUNCTION ---
def format_math_expressions(text):
    """Formats both display and inline math in a string."""
    if text is None:
        return None
    processed_text = re.sub(
        PATTERN_DOUBLE, format_display_math_block, text, flags=re.MULTILINE
    )
    processed_text = re.sub(PATTERN_SINGLE, format_inline_math, processed_text)
    processed_text = re.sub(r"\n{3,}", "\n\n", processed_text)
    return processed_text.strip()


# --- CLIPBOARD FORMATTER LOOP ---
def clipboard_formatter_loop():
    print("Clipboard formatter started.")
    try:
        recent_value = pyperclip.paste()
    except pyperclip.PyperclipException:
        recent_value = ""

    while True:
        try:
            current_clipboard_content = pyperclip.paste()
            if (
                current_clipboard_content != recent_value
                and current_clipboard_content
                and not current_clipboard_content.isspace()
            ):
                recent_value = current_clipboard_content
                if re.search(PATTERN_SINGLE, current_clipboard_content) or re.search(
                    PATTERN_DOUBLE, current_clipboard_content, re.MULTILINE
                ):
                    formatted_text = format_math_expressions(current_clipboard_content)
                    if formatted_text != current_clipboard_content:
                        pyperclip.copy(formatted_text)
                        recent_value = formatted_text
                        print("--- Auto-formatted LaTeX in clipboard ---")
            time.sleep(0.5)
        except (pyperclip.PyperclipException, KeyboardInterrupt):
            break
        except Exception:
            time.sleep(2)


# --- LaTeX Delimiter Conversion ---
def convert_latex_delimiters(text):
    """Converts $...$ and $$...$$ to Anki's \(...\) and \[...\] format."""
    text = re.sub(r"\$\$(.*?)\$\$", r"\[\1\]", text, flags=re.DOTALL)
    text = re.sub(r"\$(.*?)\$", r"\( \1 \)", text)
    return text


# --- NEW, ROBUST PARSING FUNCTION ---
def parse_flashcards_from_text(text_content):
    """
    Parses flashcards from a string using the reliable "Front:"/"Back:" format.
    """
    parsed_cards = []
    if not text_content or text_content.isspace():
        return parsed_cards

    # Split the entire text into potential cards based on the separator
    potential_card_blocks = text_content.split("---")

    for i, block in enumerate(potential_card_blocks):
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()
        front_index = -1
        back_index = -1

        # Find the line indices for the "Front:" and "Back:" labels
        for j, line in enumerate(lines):
            clean_line = line.strip().lower()
            # Check for "Front:" (plain or bold)
            if clean_line.startswith("front:") or clean_line.startswith("**front:"):
                if front_index == -1:  # Capture only the first occurrence
                    front_index = j
            # Check for "Back:" (plain or bold)
            elif clean_line.startswith("back:") or clean_line.startswith("**back:"):
                if back_index == -1 and front_index != -1:  # Ensure "Front:" came first
                    back_index = j
                    break  # Found both labels, no need to search further in this block

        # If both labels were found in the correct order, extract the content
        if front_index != -1 and back_index != -1 and back_index > front_index:
            question_lines = lines[front_index + 1 : back_index]
            answer_lines = lines[back_index + 1 :]

            question = "\n".join(question_lines).strip()
            answer = "\n".join(answer_lines).strip()

            if question and answer:
                parsed_cards.append({"question": question, "answer": answer})
            else:
                print(
                    f"DEBUG: Parsed block {i+1} but question or answer was empty. Skipping."
                )
        else:
            print(
                f"DEBUG: Failed to find valid 'Front:' followed by 'Back:' in block {i+1}. Skipping."
            )

    return parsed_cards


# --- RELIABLE AUTOMATION FUNCTION ---
def automate_anki_card_entry(cards_to_process):
    """Automates typing into Anki with deliberate pauses to ensure reliability."""
    if not cards_to_process:
        print("INFO: No valid cards were parsed. Automation skipped.")
        return

    print(f"\nINFO: Starting Anki card creation for {len(cards_to_process)} card(s)...")
    modifier_key = "command" if sys.platform == "darwin" else "ctrl"

    def robust_paste(text):
        """Pastes text reliably by holding modifier key down."""
        pyperclip.copy(text)
        time.sleep(0.1)  # Crucial pause for clipboard to update
        pyautogui.keyDown(modifier_key)
        pyautogui.press("v")
        pyautogui.keyUp(modifier_key)
        time.sleep(0.1)  # Pause for paste to complete

    for i, card_data in enumerate(cards_to_process):
        print(f"--- Processing Card {i+1}/{len(cards_to_process)} ---")

        try:
            # 1. Paste Question
            print("Step 1: Pasting Question...")
            question_text = convert_latex_delimiters(card_data["question"])
            robust_paste(question_text)

            # 2. Move to next field
            print("Step 2: Tabbing to Answer field...")
            pyautogui.press("tab")
            time.sleep(0.2)

            # 3. Paste Answer
            print("Step 3: Pasting Answer...")
            answer_text = convert_latex_delimiters(card_data["answer"])
            robust_paste(answer_text)

            # 4. Save the card and wait
            print(f"Step 4: Saving card with '{modifier_key} + enter'...")
            pyautogui.hotkey(modifier_key, "enter")
            time.sleep(0.75)  # Crucial: Give Anki time to save and reset

        except Exception as e:
            print(
                f"ERROR: A keyboard automation step failed for card {i+1}. Aborting. Details: {e}"
            )
            return

        print(f"SUCCESS: Card {i+1} created.")

    print("\n--- All specified flashcards processed! ---")


# --- Hotkey Listener Callback ---
def on_activate_hotkey_callback():
    global processing_cards_flag
    if processing_cards_flag:
        print("INFO: Card processing already in progress.")
        return

    processing_cards_flag = True
    print("\n\n=== Hotkey Activated: Starting Anki Card Creation ===")

    try:
        card_data_string = pyperclip.paste()
        if not card_data_string or card_data_string.isspace():
            print("INFO: Clipboard is empty. No cards to process.")
            return

        print("INFO: Parsing flashcard data from clipboard...")
        parsed_cards = parse_flashcards_from_text(card_data_string)

        if not parsed_cards:
            print("ERROR: No valid cards found in clipboard. Please check your format:")
            print("- Cards must be separated by '---'")
            print("- Each card must contain 'Front:' and 'Back:' on their own lines.")
            return

        print(f"SUCCESS: Parsed {len(parsed_cards)} card(s).")
        print("\n!!! YOU HAVE 3 SECONDS TO FOCUS THE ANKI 'ADD' WINDOW !!!")
        print("!!! Make sure the cursor is in the FIRST field (e.g., 'Front'). !!!")

        for i in range(3, 0, -1):
            print(f"Starting automation in {i}...")
            time.sleep(1)

        print("\nACTION: Starting keyboard automation now!")
        automate_anki_card_entry(parsed_cards)

    except Exception as e:
        print(f"ERROR: An unexpected error occurred during hotkey activation: {e}")
    finally:
        processing_cards_flag = False
        print("=== Ready for next hotkey activation. ===")


# --- Main Function ---
def main():
    hotkey_str = "<cmd>+=" if sys.platform == "darwin" else "<ctrl>+="
    print("--- Anki Automation & LaTeX Formatter ---")
    print(f"\nPress {hotkey_str} to process clipboard content into Anki.")
    print("Press Ctrl+C in this terminal to stop.")

    formatter_thread = threading.Thread(target=clipboard_formatter_loop, daemon=True)
    formatter_thread.start()

    try:
        with pynput_keyboard.GlobalHotKeys(
            {hotkey_str: on_activate_hotkey_callback}
        ) as listener:
            listener.join()
    except Exception as e:
        print(f"\n--- FATAL ERROR ---")
        print(f"Failed to start hotkey listener: {e}")
        if sys.platform == "darwin":
            print(
                "\nmacOS Users: Grant 'Input Monitoring' and 'Accessibility' permissions in System Settings."
            )


if __name__ == "__main__":
    main()
