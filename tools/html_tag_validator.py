import re
import sys
from pathlib import Path

VOID_TAGS = set(['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'])

def find_tags(text):
    # remove comments
    text_no_comments = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    # We'll iterate and also track line numbers
    tags = []
    for m in re.finditer(r'<(/?)([A-Za-z0-9:-]+)([^>]*)>', text_no_comments):
        full = m.group(0)
        closing = m.group(1) == '/'
        name = m.group(2).lower()
        rest = m.group(3)
        start = m.start()
        # compute line number
        line = text_no_comments.count('\n', 0, start) + 1
        # detect self-closing
        self_closing = False
        if rest.strip().endswith('/'):
            self_closing = True
        tags.append((line, closing, name, full, self_closing))
    return tags


def validate(path):
    txt = Path(path).read_text(encoding='utf-8')
    # ignore content inside script and style tags to avoid angle brackets issues
    # replace their content with placeholders
    txt = re.sub(r'<script[^>]*>.*?</script>', '<script></script>', txt, flags=re.S|re.I)
    txt = re.sub(r'<style[^>]*>.*?</style>', '<style></style>', txt, flags=re.S|re.I)

    tags = find_tags(txt)
    stack = []
    errors = []
    for line, closing, name, full, self_closing in tags:
        if name == '!doctype':
            continue
        if closing:
            if not stack:
                errors.append((line, 'unexpected-closing', name, full))
            else:
                top_name, top_line = stack[-1]
                if top_name == name:
                    stack.pop()
                else:
                    # search backwards for a matching open
                    idx = None
                    for i in range(len(stack)-1, -1, -1):
                        if stack[i][0] == name:
                            idx = i
                            break
                    if idx is None:
                        errors.append((line, 'mismatched-closing', name, full, top_name, top_line))
                    else:
                        errors.append((line, 'mismatched-closing-nested', name, full, top_name, top_line))
                        # pop until idx inclusive
                        stack = stack[:idx]
        else:
            if name in VOID_TAGS or self_closing:
                continue
            # push
            stack.append((name, line))
    # any unclosed
    for name, line in stack:
        errors.append((line, 'unclosed', name, None))
    return errors

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: html_tag_validator.py path/to/file.html')
        sys.exit(2)
    path = sys.argv[1]
    errs = validate(path)
    if not errs:
        print('No tag mismatches or unclosed tags detected.')
        sys.exit(0)
    print('Found %d issues:' % len(errs))
    for e in errs:
        if e[1] == 'unexpected-closing':
            print(f'Line {e[0]}: unexpected closing tag </{e[2]}> ({e[3]})')
        elif e[1] == 'mismatched-closing':
            print(f'Line {e[0]}: mismatched closing tag </{e[2]}> (expected </{e[4]}> opened at line {e[5]})')
        elif e[1] == 'mismatched-closing-nested':
            print(f'Line {e[0]}: nested mismatched closing </{e[2]}> (top was <{e[4]}> opened at {e[5]})')
        elif e[1] == 'unclosed':
            print(f'Line {e[0]}: unclosed tag <{e[2]}>')
    sys.exit(1)
