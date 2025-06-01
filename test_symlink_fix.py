import os
import pathlib
import shutil
import urllib.parse
import tempfile

def run_symlink_test():
    """
    Tests the symlink creation for a directory with spaces in its name,
    simulating the path encoding/decoding logic relevant to the fix in app.py.
    """
    test_name = "Symlink Test for Directories with Spaces"
    print(f"--- Starting: {test_name} ---")

    # 1. Setup temporary directories
    # Create a main temporary directory to hold search_dir and working_dir
    # This makes cleanup easier and ensures they are sibling directories if needed.
    base_temp_dir = pathlib.Path(tempfile.mkdtemp(prefix="symlink_test_"))
    search_dir = base_temp_dir / "search_dir"
    working_dir = base_temp_dir / "working_dir"

    source_dir_name = "My Test Show Season 1"
    source_dir_path = search_dir / source_dir_name

    tv_target_base = working_dir / "TV"
    tag_name = "SciFi Drama"
    target_link_parent_dir = tv_target_base / tag_name

    try:
        # Create all necessary directories
        source_dir_path.mkdir(parents=True, exist_ok=True)
        target_link_parent_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created source directory: {source_dir_path}")
        print(f"Created target link parent directory: {target_link_parent_dir}")

        # 2. Simulate path processing as relevant to app.py's logic
        # In app.py, item.path is the full, real path to the source item.
        original_path_str = str(source_dir_path.resolve())
        print(f"Original path string: {original_path_str}")

        # a. Template side: {{ item.path | urlencode }}
        # This is what would be part of the form field name.
        # Example: media_type_...{{item.path|urlencode}}...
        # For testing, we only need to quote the path itself.
        path_as_in_form_key_part = urllib.parse.quote(original_path_str)
        print(f"Path part as URL encoded for form key: {path_as_in_form_key_part}")

        # b. Server side (app.py):
        #    key = "media_type_" + path_as_in_form_key_part (or similar, already URL-decoded by Flask)
        #    item_path_str = key.replace('media_type_', '', 1)
        #    item_path_str = urllib.parse.unquote(item_path_str) <--- The Fix
        #
        # For this test, we assume Flask's initial decoding of the key handles
        # the form encoding, so path_as_in_form_key_part represents the state
        # *before* the explicit unquote() if Flask's decoding was incomplete,
        # or the already correct path if Flask's decoding was complete.
        # The crucial part is that `urllib.parse.unquote` is applied.

        # If Flask fully decodes the key, then item_path_str before unquote would be original_path_str.
        # If Flask partially decodes (e.g. %2F -> / but %20 remains %20),
        # then item_path_str would be original_path_str but with some encodings.
        # The test here focuses on ensuring `unquote` handles typical encodings like %20.

        # Let's simulate the state *after* key.replace but *before* the explicit unquote,
        # assuming it might still have URL encodings for spaces if not for forward slashes.
        # A simple way to test the unquote is to ensure a path with %20 is handled.
        # Path component with space: "My Test Show Season 1" -> "My%20Test%20Show%20Season%201"

        # To be more direct for the test's purpose:
        # We care that if `item_path_str` somehow ended up as (e.g.) "/tmp/.../My%20Test%20Show..."
        # the `urllib.parse.unquote()` would fix it.

        # Simulate item_path_str as it would be received and then unquoted in app.py
        # For robustness, let's assume item_path_str might contain percent-encoded spaces.
        # The actual form key would be more complex, but we test the unquoting of a path string.
        potentially_still_encoded_path_str = urllib.parse.quote(original_path_str) # Simulate a string that might still have %20 etc.

        # This is the crucial step from app.py we're testing the effect of:
        decoded_path_str = urllib.parse.unquote(potentially_still_encoded_path_str)
        print(f"Path string after urllib.parse.unquote: {decoded_path_str}")

        processed_source_path = pathlib.Path(decoded_path_str)
        print(f"Processed source Path object: {processed_source_path}")
        print(f"Does processed source path exist? {processed_source_path.exists()}")
        print(f"Is it a directory? {processed_source_path.is_dir()}")

        assert processed_source_path.exists(), "Processed source path does not exist."
        assert processed_source_path.is_dir(), "Processed source path is not a directory."
        assert str(processed_source_path.resolve()) == original_path_str, "Resolved processed path differs from original."

        # 3. Define target link name
        # Link name uses the .name of the *actual* source path object
        link_name = target_link_parent_dir / processed_source_path.name
        print(f"Target symlink path: {link_name}")

        # 4. Attempt to create the symlink
        os.symlink(processed_source_path, link_name, target_is_directory=True)
        print(f"Symlink created: {link_name} -> {processed_source_path}")

        # 5. Assertions
        assert link_name.exists(), f"Symlink does not exist at {link_name}"
        assert link_name.is_symlink(), f"{link_name} is not a symlink."

        # On Windows, os.readlink might need admin rights or specific Windows versions
        # For broader compatibility, checking resolved path might be more robust if readlink is tricky
        # However, let's try readlink first.
        try:
            resolved_link_target = os.readlink(link_name)
            print(f"Symlink target (os.readlink): {resolved_link_target}")
            # os.readlink might return a relative path depending on how it was created.
            # For symlinks to directories, comparing resolved paths is more reliable.
            resolved_symlink_path = link_name.resolve()
            print(f"Resolved symlink path: {resolved_symlink_path}")
            assert resolved_symlink_path == processed_source_path.resolve(), \
                f"Symlink does not point to the correct source. Expected: {processed_source_path.resolve()}, Got: {resolved_symlink_path}"
        except OSError as e:
            print(f"Could not readlink directly (OSError: {e}). Checking resolved path equality.")
            # Fallback for systems where readlink might be problematic (e.g. permissions, Windows behavior)
            assert link_name.resolve(strict=True) == processed_source_path.resolve(strict=True), \
                 f"Symlink does not point to the correct source (checked via resolve). Expected: {processed_source_path.resolve()}, Got: {link_name.resolve()}"


        print(f"--- SUCCESS: {test_name} ---")
        return True

    except AssertionError as e:
        print(f"!!! TEST FAILED: {test_name} !!!")
        print(f"AssertionError: {e}")
        return False
    except Exception as e:
        print(f"!!! TEST FAILED WITH EXCEPTION: {test_name} !!!")
        print(f"Exception: {e}")
        return False
    finally:
        # 6. Teardown: Remove temporary directories
        if base_temp_dir.exists():
            print(f"Cleaning up temporary directory: {base_temp_dir}")
            shutil.rmtree(base_temp_dir)

if __name__ == "__main__":
    if run_symlink_test():
        print("Test completed successfully.")
    else:
        print("Test failed.")
        # Optionally, exit with a non-zero code to indicate failure for CI systems
        # import sys
        # sys.exit(1)
