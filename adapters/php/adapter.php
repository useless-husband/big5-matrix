<?php
// Adapter for PHP's mbstring extension (BIG-5, CP950). See big5matrix/protocol.py.
//
// Decoding uses mb_convert_encoding with U+FFFD as the substitute character. mbstring has no
// strict encoding mode, so encoding uses the "long" substitute mode, which writes U+XXXX in
// ASCII for a character it cannot encode; the adapter reports that as an error. No single
// character legitimately encodes to text containing "U+", and the multi-character inputs in
// this study contain no "U" or "+".

if ($argc !== 2) {
    fwrite(STDERR, "usage: adapter.php --version | adapter.php <encoding>\n");
    exit(2);
}
if ($argv[1] === '--version') {
    echo "version=PHP " . PHP_VERSION . " mbstring " . phpversion('mbstring') . "\n";
    echo "key=" . PHP_VERSION . "\n";
    exit(0);
}
$codec = $argv[1];
if (!in_array($codec, mb_list_encodings(), true)) {
    fwrite(STDERR, "unknown encoding $codec\n");
    exit(2);
}

function code_points(string $utf8): string
{
    if ($utf8 === '') {
        return '-';
    }
    $out = [];
    foreach (mb_str_split($utf8, 1, 'UTF-8') as $ch) {
        $out[] = sprintf('%04X', mb_ord($ch, 'UTF-8'));
    }
    return implode(' ', $out);
}

$buf = '';
while (($line = fgets(STDIN)) !== false) {
    [$op, $arg] = explode("\t", rtrim($line, "\n"));
    if ($op === 'd') {
        mb_substitute_character(0xFFFD);
        $res = code_points(mb_convert_encoding(hex2bin($arg), 'UTF-8', $codec));
    } elseif ($op === 'e') {
        $s = '';
        foreach (explode(' ', $arg) as $cp) {
            $s .= mb_chr(hexdec($cp), 'UTF-8');
        }
        mb_substitute_character('long');
        $b = mb_convert_encoding($s, $codec, 'UTF-8');
        if (str_contains($b, 'U+') && !str_contains($s, 'U')) {
            $res = '!';
        } else {
            $res = $b === '' ? '-' : strtoupper(bin2hex($b));
        }
    } else {
        throw new Exception("bad op $op");
    }
    $buf .= "$op\t$arg\t$res\n";
    if (strlen($buf) > 65536) {
        fwrite(STDOUT, $buf);
        $buf = '';
    }
}
fwrite(STDOUT, $buf);
