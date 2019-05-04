# Per Google's recommendation [1], this is copied from [2], with
# the line ending match adjusted to find spans of whitespace.
#
# The original [2] is used under the Apache License, Version 2.0.
#
# [1] https://github.com/google/diff-match-patch/wiki/Line-or-Word-Diffs#word-mode
# [2] https://github.com/google/diff-match-patch/blob/858b3812cc02e7d48da4beebb21d4d80dc1d3062/python3/diff_match_patch.py
import re


def diff_wordsToChars(text1, text2):
  """Split two texts into an array of strings.  Reduce the texts to a string
  of hashes where each Unicode character represents one line.

  Args:
    text1: First string.
    text2: Second string.

  Returns:
    Three element tuple, containing the encoded text1, the encoded text2 and
    the array of unique strings.  The zeroth element of the array of unique
    strings is intentionally blank.
  """
  lineArray = []  # e.g. lineArray[4] == "Hello\n"
  lineHash = {}   # e.g. lineHash["Hello\n"] == 4

  # "\x00" is a valid character, but various debuggers don't like it.
  # So we'll insert a junk entry to avoid generating a null character.
  lineArray.append('')

  def next_word_end(text, start):
    """Find the next word end (any whitespace) after `start`.
    """
    pattern = re.compile(r"([^ \t\n]+)[ \t\n]")
    match = pattern.search(text, start)
    if not match:
      return -1
    return start + len(match.group(1))

  def diff_linesToCharsMunge(text):
    """Split a text into an array of strings.  Reduce the texts to a string
    of hashes where each Unicode character represents one line.
    Modifies linearray and linehash through being a closure.

    Args:
      text: String to encode.

    Returns:
      Encoded string.
    """
    chars = []
    # Walk the text, pulling out a substring for each line.
    # text.split('\n') would would temporarily double our memory footprint.
    # Modifying text would create many large strings to garbage collect.
    lineStart = 0
    lineEnd = -1
    while lineEnd < len(text) - 1:
      lineEnd = next_word_end(text, lineStart)
      if lineEnd == -1:
        lineEnd = len(text) - 1
      line = text[lineStart:lineEnd + 1]

      if line in lineHash:
        chars.append(chr(lineHash[line]))
      else:
        if len(lineArray) == maxLines:
          # Bail out at 1114111 because chr(1114112) throws.
          line = text[lineStart:]
          lineEnd = len(text)
        lineArray.append(line)
        lineHash[line] = len(lineArray) - 1
        chars.append(chr(len(lineArray) - 1))
      lineStart = lineEnd + 1
    return "".join(chars)

  # Allocate 2/3rds of the space for text1, the rest for text2.
  maxLines = 666666
  chars1 = diff_linesToCharsMunge(text1)
  maxLines = 1114111
  chars2 = diff_linesToCharsMunge(text2)
  return (chars1, chars2, lineArray)
