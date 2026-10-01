#!/usr/bin/perl
# Perl Encode: a truncated multibyte character at the end of the input disappears, with no
# U+FFFD (FB_DEFAULT) and no error (FB_CROAK). perldoc Encode: with CHECK = 0 "decoding
# replace[s] any malformed character with ... U+FFFD"; with CHECK = 1 "methods immediately die".
use strict;
use warnings;
use Encode qw(decode);
printf "Encode %s\n", $Encode::VERSION;
for my $enc (qw(big5-eten cp950 big5-hkscs shiftjis euc-kr)) {
    my %lead = ('big5-eten' => "\xA4", cp950 => "\xA4", 'big5-hkscs' => "\xA4", shiftjis => "\x82", 'euc-kr' => "\xB0");
    for my $check (Encode::FB_DEFAULT, Encode::FB_CROAK) {
        my $bytes = "a" . $lead{$enc};
        my $s = eval { decode($enc, $bytes, $check) };
        printf "%-10s check=%d: %s\n", $enc, $check,
            defined $s ? join(' ', map { sprintf 'U+%04X', ord } split //, $s) : "died: $@";
    }
}
