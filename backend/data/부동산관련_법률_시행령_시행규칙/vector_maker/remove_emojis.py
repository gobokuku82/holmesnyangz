"""
Remove all emojis from Python files
"""
import os
import re
from pathlib import Path

def remove_emojis(text):
    """Remove emoji characters from text"""
    # Pattern to match most emojis
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        u"\U00002600-\U000026FF"  # Miscellaneous Symbols
        u"\U00002700-\U000027BF"  # Dingbats
        "]+", flags=re.UNICODE)

    return emoji_pattern.sub('', text)

def process_file(file_path):
    """Process a single Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if file contains emojis
        original_len = len(content)
        cleaned_content = remove_emojis(content)

        if len(cleaned_content) < original_len:
            # Save cleaned content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"Cleaned: {file_path.name}")
            return True
        else:
            print(f"No emojis found: {file_path.name}")
            return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function"""
    current_dir = Path(__file__).parent

    # Get all Python files
    py_files = list(current_dir.glob("*.py"))

    print(f"Found {len(py_files)} Python files")
    print("="*50)

    cleaned_count = 0
    for py_file in py_files:
        if py_file.name != "remove_emojis.py":  # Skip this script
            if process_file(py_file):
                cleaned_count += 1

    print("="*50)
    print(f"Cleaned {cleaned_count} files")

if __name__ == "__main__":
    main()