"""Test the markdown stripping functionality."""

import json

from src.integrations.llm_client import _strip_markdown_json

# Test cases
test_cases = [
    # Case 1: Markdown wrapped JSON
    (
        '```json\n{\n  "title": "Sample Title",\n  "score": 95\n}\n```',
        '{\n  "title": "Sample Title",\n  "score": 95\n}',
    ),
    # Case 2: Plain markdown wrapped
    ('```\n{"title": "Test", "score": 100}\n```', '{"title": "Test", "score": 100}'),
    # Case 3: Already clean JSON
    ('{"title": "Clean", "score": 50}', '{"title": "Clean", "score": 50}'),
    # Case 4: JSON with whitespace
    ('  \n{"title": "Whitespace", "score": 75}\n  ', '{"title": "Whitespace", "score": 75}'),
]

print("Testing markdown stripping functionality:\n")
all_passed = True

for i, (input_text, expected_output) in enumerate(test_cases, 1):
    result = _strip_markdown_json(input_text)
    passed = result == expected_output
    all_passed = all_passed and passed

    print(f"Test {i}: {'✓ PASS' if passed else '✗ FAIL'}")
    if not passed:
        print(f"  Input: {repr(input_text[:50])}")
        print(f"  Expected: {repr(expected_output[:50])}")
        print(f"  Got: {repr(result[:50])}")

    # Also test if it's valid JSON
    try:
        json.loads(result)
        print("  JSON valid: ✓")
    except json.JSONDecodeError as e:
        print(f"  JSON valid: ✗ ({e})")
        all_passed = False
    print()

print(f"\n{'All tests passed! ✓' if all_passed else 'Some tests failed ✗'}")
