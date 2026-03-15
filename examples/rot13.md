# ROT13 Cipher

Read text from stdin until EOF. Apply ROT13 encoding to each alphabetic character:
- 'a'-'m' → 'n'-'z', 'n'-'z' → 'a'-'m'
- 'A'-'M' → 'N'-'Z', 'N'-'Z' → 'A'-'M'
- Non-alphabetic characters pass through unchanged

Print the encoded text to stdout. Exit with code 0.
