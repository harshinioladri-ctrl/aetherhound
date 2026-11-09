"""Morse encode/decode + OOK (on/off keying) decoder for covert-channel pulses."""
import numpy as np
CODE = {'A':'.-','B':'-...','C':'-.-.','D':'-..','E':'.','F':'..-.','G':'--.','H':'....',
        'I':'..','J':'.---','K':'-.-','L':'.-..','M':'--','N':'-.','O':'---','P':'.--.',
        'Q':'--.-','R':'.-.','S':'...','T':'-','U':'..-','V':'...-','W':'.--','X':'-..-',
        'Y':'-.--','Z':'--..','0':'-----','1':'.----','2':'..---','3':'...--','4':'....-',
        '5':'.....','6':'-....','7':'--...','8':'---..','9':'----.'}
INV = {v: k for k, v in CODE.items()}

def encode_envelope(text, unit_samples):
    """Return a boolean on/off envelope (samples) keyed with Morse for `text`."""
    out = []
    for w, word in enumerate(text.upper().split()):
        if w: out += [False] * (7 * unit_samples)
        for li, ch in enumerate(word):
            if ch not in CODE: continue
            if li: out += [False] * (3 * unit_samples)
            for si, s in enumerate(CODE[ch]):
                if si: out += [False] * unit_samples
                out += [True] * ((1 if s == '.' else 3) * unit_samples)
    return np.array(out, dtype=bool)

def decode_ook(on):
    """Decode a per-frame on/off trace -> dict(unit_frames, bits, morse, text)."""
    on = np.asarray(on, bool)
    on = np.convolve(on.astype(int), np.ones(3, int), 'same') >= 2   # de-glitch
    runs, prev, c = [], None, 0
    for v in on:
        if v == prev: c += 1
        else:
            if prev is not None: runs.append((prev, c))
            prev, c = v, 1
    if prev is not None: runs.append((prev, c))
    while runs and not runs[0][0]: runs.pop(0)
    while runs and not runs[-1][0]: runs.pop()
    ons = [l for v, l in runs if v]
    if not ons: return dict(unit_frames=0, bits="", morse="", text="")
    m = min(ons)
    unit = float(np.median([l for l in ons if l <= 1.8 * m]))
    bits = ''.join(('1' if v else '0') * max(1, round(l / unit)) for v, l in runs)
    words, cur = [[]], ''
    for v, l in runs:
        u = l / unit
        if v: cur += '.' if u < 2 else '-'
        elif u >= 2:
            words[-1].append(cur); cur = ''
            if u >= 5: words.append([])
    if cur: words[-1].append(cur)
    morse = ' / '.join(' '.join(w) for w in words)
    text = ' '.join(''.join(INV.get(c, '?') for c in w) for w in words)
    return dict(unit_frames=round(unit, 2), bits=bits, morse=morse, text=text)
